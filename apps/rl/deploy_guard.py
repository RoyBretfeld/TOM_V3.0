"""
TOM v3.0 - RL Deploy Guard
Shadow/A-B Deployment Guard für sichere Policy-Varianten-Deployment
"""

import logging
import json
import os
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass

from apps.rl.policy_bandit import PolicyBandit, get_policy_stats
from apps.rl.reward_calc import calc_reward
from apps.monitor.metrics import (
    record_policy_pull, update_active_variants, 
    update_blacklisted_variants, record_escalation
)

logger = logging.getLogger(__name__)

@dataclass
class DeployConfig:
    """Konfiguration für Deployment-Guard"""
    traffic_split_new: float = 0.1  # 10% für neue Varianten
    traffic_split_uncertain: float = 0.05  # 5% für unsichere Varianten
    base_variant: str = "v1a"  # Fallback-Variante
    blacklist_threshold: float = -0.2  # Reward-Schwellwert für Blacklist
    min_pulls_for_blacklist: int = 20  # Min. Pulls vor Blacklist
    min_pulls_for_confidence: int = 10  # Min. Pulls für Konfidenz
    confidence_threshold: float = 0.7  # Konfidenz-Schwellwert
    max_active_variants: int = 12  # Max. aktive Varianten

class DeployGuard:
    """Deployment-Guard für sichere Policy-Varianten-Deployment"""
    
    def __init__(self, config: Optional[DeployConfig] = None):
        self.config = config or DeployConfig()
        self.bandit = PolicyBandit()
        self.blacklisted_variants: Set[str] = set()
        self.active_variants: Set[str] = set()
        self._load_state()
        
    def _load_state(self):
        """Lädt Deployment-State aus Datei"""
        state_file = os.path.join('data', 'rl', 'deploy_state.json')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.blacklisted_variants = set(data.get('blacklisted_variants', []))
                self.active_variants = set(data.get('active_variants', []))
                logger.info(f"Deployment-State geladen: {len(self.active_variants)} aktive, {len(self.blacklisted_variants)} blacklisted")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Deployment-States: {e}")
                self._init_default_state()
        else:
            self._init_default_state()
            
    def _save_state(self):
        """Speichert Deployment-State in Datei"""
        os.makedirs(os.path.dirname(os.path.join('data', 'rl', 'deploy_state.json')), exist_ok=True)
        state_file = os.path.join('data', 'rl', 'deploy_state.json')
        
        data = {
            'blacklisted_variants': list(self.blacklisted_variants),
            'active_variants': list(self.active_variants),
            'last_update': datetime.now().isoformat()
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
    def _init_default_state(self):
        """Initialisiert Standard-State"""
        self.active_variants = {self.config.base_variant}
        self.blacklisted_variants = set()
        self._save_state()
        
    def select_variant_for_deployment(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Wählt Policy-Variante für Deployment basierend auf Traffic-Split-Regeln
        Returns: Policy-Variante-ID
        """
        try:
            # 1. Blacklist-Check
            self._update_blacklist()
            
            # 2. Verfügbare Varianten ermitteln
            available_variants = self._get_available_variants()
            
            if not available_variants:
                logger.warning("Keine verfügbaren Varianten, verwende Base-Variante")
                return self.config.base_variant
                
            # 3. Traffic-Split-Logik
            import random
            rand = random.random()
            
            # Neue Varianten (weniger als min_pulls_for_confidence)
            new_variants = [v for v in available_variants if self._is_new_variant(v)]
            if new_variants and rand < self.config.traffic_split_new:
                selected = random.choice(new_variants)
                logger.info(f"Neue Variante ausgewählt: {selected}")
                record_policy_pull(selected)
                return selected
                
            # Unsichere Varianten (niedrige Konfidenz)
            uncertain_variants = [v for v in available_variants if self._is_uncertain_variant(v)]
            if uncertain_variants and rand < self.config.traffic_split_uncertain:
                selected = random.choice(uncertain_variants)
                logger.info(f"Unsichere Variante ausgewählt: {selected}")
                record_policy_pull(selected)
                return selected
                
            # Bandit-Auswahl für restlichen Traffic
            bandit_selected = self.bandit.select(context)
            if bandit_selected and bandit_selected in available_variants:
                logger.info(f"Bandit-Variante ausgewählt: {bandit_selected}")
                record_policy_pull(bandit_selected)
                return bandit_selected
                
            # Fallback zur Base-Variante
            logger.info(f"Fallback zur Base-Variante: {self.config.base_variant}")
            record_policy_pull(self.config.base_variant)
            return self.config.base_variant
            
        except Exception as e:
            logger.error(f"Fehler bei Varianten-Auswahl: {e}")
            return self.config.base_variant
            
    def _get_available_variants(self) -> List[str]:
        """Gibt verfügbare (nicht-blacklisted) Varianten zurück"""
        all_variants = set(self.bandit.state.variants.keys())
        available = all_variants - self.blacklisted_variants
        return list(available)
        
    def _is_new_variant(self, variant_id: str) -> bool:
        """Prüft ob Variante neu ist (weniger als min_pulls_for_confidence)"""
        stats = get_policy_stats(variant_id)
        return stats.get('pulls', 0) < self.config.min_pulls_for_confidence
        
    def _is_uncertain_variant(self, variant_id: str) -> bool:
        """Prüft ob Variante unsicher ist (niedrige Konfidenz)"""
        stats = get_policy_stats(variant_id)
        confidence = stats.get('confidence', 0.0)
        pulls = stats.get('pulls', 0)
        
        return (pulls >= self.config.min_pulls_for_confidence and 
                confidence < self.config.confidence_threshold)
                
    def _update_blacklist(self):
        """Aktualisiert Blacklist basierend auf Reward-Schwellwerten"""
        updated = False
        
        for variant_id in list(self.active_variants):
            if variant_id in self.blacklisted_variants:
                continue
                
            stats = get_policy_stats(variant_id)
            pulls = stats.get('pulls', 0)
            mean_reward = stats.get('mean_reward', 0.0)
            
            # Blacklist-Kriterien prüfen
            if (pulls >= self.config.min_pulls_for_blacklist and 
                mean_reward < self.config.blacklist_threshold):
                
                self.blacklisted_variants.add(variant_id)
                self.active_variants.discard(variant_id)
                updated = True
                logger.warning(f"Variante {variant_id} blacklisted: reward={mean_reward:.3f}, pulls={pulls}")
                record_escalation(variant_id)
                
        if updated:
            self._save_state()
            update_active_variants(len(self.active_variants))
            update_blacklisted_variants(len(self.blacklisted_variants))
            
    def add_variant_to_deployment(self, variant_id: str) -> bool:
        """
        Fügt neue Variante zum Deployment hinzu
        Returns: True wenn erfolgreich hinzugefügt
        """
        try:
            if variant_id in self.blacklisted_variants:
                logger.warning(f"Variante {variant_id} ist blacklisted")
                return False
                
            if len(self.active_variants) >= self.config.max_active_variants:
                logger.warning(f"Maximale Anzahl aktiver Varianten erreicht: {self.config.max_active_variants}")
                return False
                
            self.active_variants.add(variant_id)
            self._save_state()
            update_active_variants(len(self.active_variants))
            
            logger.info(f"Variante {variant_id} zum Deployment hinzugefügt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Hinzufügen der Variante {variant_id}: {e}")
            return False
            
    def remove_variant_from_deployment(self, variant_id: str) -> bool:
        """
        Entfernt Variante aus Deployment
        Returns: True wenn erfolgreich entfernt
        """
        try:
            if variant_id not in self.active_variants:
                logger.warning(f"Variante {variant_id} ist nicht aktiv")
                return False
                
            self.active_variants.discard(variant_id)
            self._save_state()
            update_active_variants(len(self.active_variants))
            
            logger.info(f"Variante {variant_id} aus Deployment entfernt")
            return True
            
        except Exception as e:
            logger.error(f"Fehler beim Entfernen der Variante {variant_id}: {e}")
            return False
            
    def get_deployment_status(self) -> Dict[str, Any]:
        """Gibt aktuellen Deployment-Status zurück"""
        return {
            'active_variants': list(self.active_variants),
            'blacklisted_variants': list(self.blacklisted_variants),
            'total_active': len(self.active_variants),
            'total_blacklisted': len(self.blacklisted_variants),
            'config': {
                'traffic_split_new': self.config.traffic_split_new,
                'traffic_split_uncertain': self.config.traffic_split_uncertain,
                'base_variant': self.config.base_variant,
                'blacklist_threshold': self.config.blacklist_threshold,
                'min_pulls_for_blacklist': self.config.min_pulls_for_blacklist,
                'max_active_variants': self.config.max_active_variants
            }
        }
        
    def get_variant_health(self, variant_id: str) -> Dict[str, Any]:
        """Gibt Gesundheitsstatus einer Variante zurück"""
        stats = get_policy_stats(variant_id)
        
        health_status = {
            'variant_id': variant_id,
            'is_active': variant_id in self.active_variants,
            'is_blacklisted': variant_id in self.blacklisted_variants,
            'is_new': self._is_new_variant(variant_id),
            'is_uncertain': self._is_uncertain_variant(variant_id),
            'stats': stats
        }
        
        # Gesundheitsbewertung
        if variant_id in self.blacklisted_variants:
            health_status['health'] = 'blacklisted'
        elif self._is_new_variant(variant_id):
            health_status['health'] = 'new'
        elif self._is_uncertain_variant(variant_id):
            health_status['health'] = 'uncertain'
        else:
            health_status['health'] = 'stable'
            
        return health_status

# Convenience-Funktionen
_deploy_guard: Optional[DeployGuard] = None

def _get_deploy_guard() -> DeployGuard:
    global _deploy_guard
    if _deploy_guard is None:
        _deploy_guard = DeployGuard()
    return _deploy_guard

def select_variant_for_deployment(context: Optional[Dict[str, Any]] = None) -> str:
    """Wählt Policy-Variante für Deployment"""
    return _get_deploy_guard().select_variant_for_deployment(context)

def add_variant_to_deployment(variant_id: str) -> bool:
    """Fügt Variante zum Deployment hinzu"""
    return _get_deploy_guard().add_variant_to_deployment(variant_id)

def remove_variant_from_deployment(variant_id: str) -> bool:
    """Entfernt Variante aus Deployment"""
    return _get_deploy_guard().remove_variant_from_deployment(variant_id)

def get_deployment_status() -> Dict[str, Any]:
    """Gibt Deployment-Status zurück"""
    return _get_deploy_guard().get_deployment_status()

def get_variant_health(variant_id: str) -> Dict[str, Any]:
    """Gibt Varianten-Gesundheitsstatus zurück"""
    return _get_deploy_guard().get_variant_health(variant_id)
