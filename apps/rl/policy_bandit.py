"""
TOM v3.0 - RL Policy Bandit
Contextual Bandit mit Thompson Sampling für Policy-Auswahl
"""

import json
import logging
import math
import random
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class PolicyVariant:
    """Policy-Variante mit Parametern"""
    id: str
    name: str
    parameters: Dict[str, any]
    description: str = ""


@dataclass
class BanditState:
    """Zustand des Bandit-Algorithmus"""
    alpha: Dict[str, float]  # Beta-Verteilung Alpha-Parameter
    beta: Dict[str, float]   # Beta-Verteilung Beta-Parameter
    total_rewards: Dict[str, float]  # Gesamte Rewards pro Variante
    total_pulls: Dict[str, int]  # Gesamte Pulls pro Variante
    last_updated: float  # Timestamp der letzten Aktualisierung


class PolicyBandit:
    """Contextual Bandit mit Thompson Sampling für Policy-Auswahl"""
    
    def __init__(self, state_file: str = "data/rl/bandit_state.json"):
        """
        Initialisiert den Policy Bandit
        
        Args:
            state_file: Pfad zur Zustandsdatei
        """
        self.state_file = Path(state_file)
        self.logger = logging.getLogger(f"{__name__}.PolicyBandit")
        
        # Verfügbare Policy-Varianten
        self.variants: Dict[str, PolicyVariant] = {}
        
        # Bandit-Zustand
        self.state = BanditState(
            alpha={},
            beta={},
            total_rewards={},
            total_pulls={},
            last_updated=0.0
        )
        
        # Lade Zustand
        self._load_state()
    
    def add_variant(self, variant: PolicyVariant):
        """
        Fügt eine Policy-Variante hinzu
        
        Args:
            variant: Policy-Variante
        """
        self.variants[variant.id] = variant
        
        # Initialisiere Beta-Verteilung (uninformative Prior)
        if variant.id not in self.state.alpha:
            self.state.alpha[variant.id] = 1.0
            self.state.beta[variant.id] = 1.0
            self.state.total_rewards[variant.id] = 0.0
            self.state.total_pulls[variant.id] = 0
        
        self.logger.info(f"Policy-Variante hinzugefügt: {variant.id}")
    
    def select(self, context: Optional[Dict[str, any]] = None) -> str:
        """
        Wählt eine Policy-Variante basierend auf Thompson Sampling
        
        Args:
            context: Kontextinformationen (optional)
            
        Returns:
            ID der ausgewählten Policy-Variante
        """
        if not self.variants:
            raise ValueError("Keine Policy-Varianten verfügbar")
        
        # Thompson Sampling: Sample aus Beta-Verteilung
        samples = {}
        for variant_id in self.variants.keys():
            alpha = self.state.alpha[variant_id]
            beta = self.state.beta[variant_id]
            
            # Sample aus Beta-Verteilung
            sample = np.random.beta(alpha, beta)
            samples[variant_id] = sample
        
        # Wähle Variante mit höchstem Sample
        selected_id = max(samples.keys(), key=lambda k: samples[k])
        
        self.logger.debug(f"Policy ausgewählt: {selected_id} (Sample: {samples[selected_id]:.3f})")
        return selected_id
    
    def update(self, variant_id: str, reward: float):
        """
        Aktualisiert den Bandit-Zustand mit einem Reward
        
        Args:
            variant_id: ID der Policy-Variante
            reward: Erhaltener Reward (-1 bis +1)
        """
        if variant_id not in self.variants:
            self.logger.warning(f"Unbekannte Policy-Variante: {variant_id}")
            return
        
        # Normalisiere Reward auf [0, 1] für Beta-Verteilung
        normalized_reward = (reward + 1.0) / 2.0  # [-1, +1] → [0, 1]
        
        # Aktualisiere Beta-Verteilung Parameter
        self.state.alpha[variant_id] += normalized_reward
        self.state.beta[variant_id] += (1.0 - normalized_reward)
        
        # Aktualisiere Statistiken
        self.state.total_rewards[variant_id] += reward
        self.state.total_pulls[variant_id] += 1
        self.state.last_updated = self._get_timestamp()
        
        self.logger.debug(f"Bandit aktualisiert: {variant_id} -> Reward: {reward:.3f}")
        
        # Speichere Zustand
        self._save_state()
    
    def get_variant_stats(self, variant_id: str) -> Dict[str, float]:
        """
        Gibt Statistiken für eine Policy-Variante zurück
        
        Args:
            variant_id: ID der Policy-Variante
            
        Returns:
            Dictionary mit Statistiken
        """
        if variant_id not in self.variants:
            return {}
        
        pulls = self.state.total_pulls[variant_id]
        rewards = self.state.total_rewards[variant_id]
        
        if pulls == 0:
            return {
                'pulls': 0,
                'total_reward': 0.0,
                'mean_reward': 0.0,
                'alpha': self.state.alpha[variant_id],
                'beta': self.state.beta[variant_id],
                'confidence': 0.0  # Keine Daten = keine Konfidenz
            }
        
        mean_reward = rewards / pulls
        alpha = self.state.alpha[variant_id]
        beta = self.state.beta[variant_id]
        
        # Konfidenz basierend auf Beta-Verteilung
        confidence = alpha / (alpha + beta)
        
        return {
            'pulls': pulls,
            'total_reward': rewards,
            'mean_reward': mean_reward,
            'alpha': alpha,
            'beta': beta,
            'confidence': confidence
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Gibt Statistiken für alle Policy-Varianten zurück
        
        Returns:
            Dictionary mit Statistiken pro Variante
        """
        stats = {}
        for variant_id in self.variants.keys():
            stats[variant_id] = self.get_variant_stats(variant_id)
        
        return stats
    
    def get_exploration_rate(self) -> float:
        """
        Berechnet die aktuelle Exploration-Rate
        
        Returns:
            Exploration-Rate (0-1)
        """
        if not self.variants:
            return 0.0
        
        # Berechne Varianz der Beta-Verteilungen
        variances = []
        for variant_id in self.variants.keys():
            alpha = self.state.alpha[variant_id]
            beta = self.state.beta[variant_id]
            
            # Varianz der Beta-Verteilung
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            variances.append(variance)
        
        # Exploration-Rate als durchschnittliche Varianz
        return sum(variances) / len(variances) if variances else 0.0
    
    def reset_variant(self, variant_id: str):
        """
        Setzt eine Policy-Variante zurück (für neue Experimente)
        
        Args:
            variant_id: ID der Policy-Variante
        """
        if variant_id not in self.variants:
            return
        
        self.state.alpha[variant_id] = 1.0
        self.state.beta[variant_id] = 1.0
        self.state.total_rewards[variant_id] = 0.0
        self.state.total_pulls[variant_id] = 0
        
        self.logger.info(f"Policy-Variante zurückgesetzt: {variant_id}")
        self._save_state()
    
    def _load_state(self):
        """Lädt den Bandit-Zustand aus der Datei"""
        if not self.state_file.exists():
            self.logger.info("Keine Bandit-Zustandsdatei gefunden, verwende Standardwerte")
            return
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            self.state = BanditState(**data)
            self.logger.info(f"Bandit-Zustand geladen: {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Laden des Bandit-Zustands: {e}")
            # Verwende Standardwerte
            self.state = BanditState(
                alpha={},
                beta={},
                total_rewards={},
                total_pulls={},
                last_updated=0.0
            )
    
    def _save_state(self):
        """Speichert den Bandit-Zustand in die Datei"""
        try:
            # Erstelle Verzeichnis falls nötig
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
            
            self.logger.debug(f"Bandit-Zustand gespeichert: {self.state_file}")
            
        except Exception as e:
            self.logger.error(f"Fehler beim Speichern des Bandit-Zustands: {e}")
    
    def _get_timestamp(self) -> float:
        """Gibt aktuellen Timestamp zurück"""
        import time
        return time.time()


# Globale Instanz für einfachen Zugriff
policy_bandit = PolicyBandit()


def select_policy(context: Optional[Dict[str, any]] = None) -> str:
    """
    Convenience-Funktion zum Auswählen einer Policy
    
    Args:
        context: Kontextinformationen (optional)
        
    Returns:
        ID der ausgewählten Policy-Variante
    """
    return policy_bandit.select(context)


def update_policy_reward(variant_id: str, reward: float):
    """
    Convenience-Funktion zum Aktualisieren eines Policy-Rewards
    
    Args:
        variant_id: ID der Policy-Variante
        reward: Erhaltener Reward (-1 bis +1)
    """
    policy_bandit.update(variant_id, reward)


def get_policy_stats() -> Dict[str, Dict[str, float]]:
    """
    Convenience-Funktion für Policy-Statistiken
    
    Returns:
        Dictionary mit Statistiken pro Variante
    """
    return policy_bandit.get_all_stats()
