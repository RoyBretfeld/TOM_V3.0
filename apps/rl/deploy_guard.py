"""
TOM v3.0 - RL Deploy Guard
Shadow/A-B Deployment Guard für sichere Policy-Varianten-Deployment
"""

from dataclasses import dataclass, field
from typing import Protocol
import json, os
import random as _random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Set, List, Optional
from pydantic import BaseModel, Field

from apps.rl.policy_bandit import PolicyBandit, get_policy_stats, PolicyVariant
from apps.monitor.metrics import (
    update_active_variants, update_blacklisted_variants, record_policy_pull, record_escalation
)

logger = logging.getLogger(__name__)

BLACKLIST_MIN_SAMPLES = 20
BLACKLIST_MIN_REWARD = -0.2

class StatsProvider(Protocol):
    def get_policy_stats(self, variant: str) -> dict: ...

def load_state(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            txt = f.read().strip()
            if not txt:
                return {}
            return json.loads(txt)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

def save_state(path: str, state: dict) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)
    if os.path.exists(path):
        os.replace(tmp, path)
    else:
        os.rename(tmp, path)

def maybe_blacklist(guard: "DeployGuard", variant: str, stats_provider: StatsProvider):
    if variant == guard.base_variant:
        return
    s = stats_provider.get_policy_stats(variant)
    n = int(s.get("samples", 0))
    r = float(s.get("reward_mean", 0.0))
    if n >= BLACKLIST_MIN_SAMPLES and r < BLACKLIST_MIN_REWARD:
        guard.blacklist.add(variant)

class DeployConfig(BaseModel):
    """Konfiguration für den Deployment Guard."""
    base_variant: str = Field(default="v1a", description="Die stabile Basis-Variante, die immer verfügbar ist.")
    traffic_split_new: float = Field(default=0.1, ge=0.0, le=1.0, description="Anteil des Traffics für neue Varianten (z.B. 0.1 = 10%).")
    traffic_split_uncertain: float = Field(default=0.2, ge=0.0, le=1.0, description="Anteil des Traffics für unsichere Varianten.")
    min_pulls_for_evaluation: int = Field(default=20, ge=1, description="Minimale Pulls, bevor eine Variante evaluiert wird.")
    blacklist_threshold_reward: float = Field(default=-0.2, le=0.0, description="Schwellenwert für den mittleren Reward, unter dem eine Variante blacklisted wird.")
    uncertainty_threshold_confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="Konfidenz-Schwellenwert, unter dem eine Variante als unsicher gilt.")
    max_active_variants: int = Field(default=5, ge=1, description="Maximale Anzahl gleichzeitig aktiver Varianten (exkl. Basis).")

class DeployState(BaseModel):
    """Speichert den Zustand des Deployment Guards für Persistenz."""
    blacklisted_variants: List[str] = Field(default_factory=list, description="Varianten, die aufgrund schlechter Performance gesperrt sind.")
    active_variants: List[str] = Field(default_factory=list, description="Varianten, die aktuell im Deployment aktiv sind (zusätzlich zur Basis).")
    last_update: str = Field(default_factory=lambda: datetime.now().isoformat(), description="Letzter Zeitpunkt der Zustandsaktualisierung.")

@dataclass
class DeployGuard:
    """
    Verwaltet das Deployment von Policy-Varianten (Shadow/A-B Deployment).
    Stellt sicher, dass neue/unsichere Varianten nur begrenzt Traffic erhalten
    und schlecht performende Varianten blacklisted werden.
    """
    variants: Set[str]
    base_variant: str
    max_traffic_per_variant: float = 0.10
    blacklist: Set[str] = field(default_factory=set)
    rng: _random.Random = field(default_factory=_random.Random)
    
    def __post_init__(self):
        self.variants = set(self.variants)
        if self.base_variant not in self.variants:
            raise ValueError(f"base_variant {self.base_variant} not in variants")
        # Basis nie sperren
        self.blacklist.discard(self.base_variant)
    
    @classmethod
    def from_config(cls, cfg: dict):
        variants = set(cfg["variants"])  # Pflichtfeld
        base = cfg.get("base_variant", next(iter(variants)))
        return cls(variants=variants, base_variant=base,
                   max_traffic_per_variant=float(cfg.get("max_traffic_per_variant", 0.10)))
    
    def pick_variant(self, eligible: list[str]) -> str:
        return self.rng.choice(eligible) if eligible else self.base_variant
    
    def get_eligible(self) -> list[str]:
        return sorted([v for v in self.variants if v not in self.blacklist and v != self.base_variant])
    
    def get_deployment_status(self) -> dict:
        return {"base_variant": self.base_variant,
                "variants": sorted(self.variants),
                "blacklist": sorted(self.blacklist),
                "eligible": self.get_eligible()}

class DeployGuardFull:
    """
    Vollständige DeployGuard-Implementierung mit allen Features
    """
    def __init__(self, config: Optional[DeployConfig] = None, state_file: str = os.path.join('data', 'rl', 'deploy_state.json')):
        self.config = config if config else DeployConfig()
        self.state_file = state_file
        self.bandit = PolicyBandit() # Der Bandit ist für die Auswahl unter den aktiven Varianten zuständig
        
        self.blacklisted_variants: Set[str] = set()
        self.active_variants: Set[str] = set()  # Leer initialisieren
        self.last_update: datetime = datetime.now()

        self._load_state()
        self._init_default_state() # Stellt sicher, dass Basis-Variante im State ist
        self._update_metrics()

    def _load_state(self):
        """Lädt Deployment-State aus Datei"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                state = DeployState.model_validate(data)
                self.blacklisted_variants = set(state.blacklisted_variants)
                self.active_variants = set(state.active_variants)
                self.last_update = datetime.fromisoformat(state.last_update)
                logger.info(f"Deployment-State geladen: {len(self.active_variants)} aktive, {len(self.blacklisted_variants)} blacklisted Varianten.")
            except Exception as e:
                logger.error(f"Fehler beim Laden des Deployment-States: {e}")
                self._init_default_state() # Fallback zu Default-State
        else:
            logger.info("Kein Deployment-State gefunden, initialisiere Standard-State.")
            self._init_default_state()

    def _save_state(self):
        """Speichert Deployment-State in Datei"""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        data = DeployState(
            blacklisted_variants=list(self.blacklisted_variants),
            active_variants=list(self.active_variants),
            last_update=datetime.now().isoformat()
        )
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(data.model_dump(), f, indent=4)
        self._update_metrics()

    def _init_default_state(self):
        """Stellt sicher, dass der Basis-State korrekt initialisiert ist."""
        # Nur hinzufügen, wenn noch nicht vorhanden
        if self.config.base_variant not in self.active_variants:
            self.active_variants.add(self.config.base_variant)
        self._save_state()

    def _update_metrics(self):
        """Aktualisiert Prometheus-Metriken."""
        update_active_variants(len(self.active_variants))
        update_blacklisted_variants(len(self.blacklisted_variants))
        # Exploration Rate wird vom Bandit selbst aktualisiert

    def _get_available_variants(self) -> List[str]:
        """Gibt alle verfügbaren Varianten zurück, die nicht blacklisted sind."""
        all_variants = set(self.bandit.state.variants.keys())
        return list(all_variants - self.blacklisted_variants)

    def _is_new_variant(self, variant_id: str) -> bool:
        """Prüft, ob eine Variante neu ist (weniger als min_pulls_for_evaluation)."""
        all_stats = get_policy_stats()
        stats = all_stats.get(variant_id, {})
        return stats.get('pulls', 0) < self.config.min_pulls_for_evaluation

    def _is_uncertain_variant(self, variant_id: str) -> bool:
        """Prüft, ob eine Variante unsicher ist (niedrige Konfidenz)."""
        all_stats = get_policy_stats()
        stats = all_stats.get(variant_id, {})
        return stats.get('pulls', 0) >= self.config.min_pulls_for_evaluation and \
               stats.get('confidence', 0.0) < self.config.uncertainty_threshold_confidence

    def _update_blacklist(self):
        """Überprüft aktive Varianten und verschiebt schlecht performende auf die Blacklist."""
        all_stats = get_policy_stats()
        for variant_id in list(self.active_variants): # Iteriere über eine Kopie
            if variant_id == self.config.base_variant:
                continue # Basis-Variante wird nie blacklisted

            stats = all_stats.get(variant_id, {})
            if stats.get('pulls', 0) >= self.config.min_pulls_for_evaluation:
                if stats.get('mean_reward', 0.0) < self.config.blacklist_threshold_reward:
                    self.blacklisted_variants.add(variant_id)
                    self.active_variants.remove(variant_id)
                    record_escalation("TOM", "general", variant_id) # Als Eskalation loggen
                    logger.warning(f"Variante {variant_id} blacklisted: reward={stats['mean_reward']:.3f}, pulls={stats['pulls']}")
        self._save_state()

    def select_variant_for_deployment(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Wählt eine Policy-Variante für das aktuelle Deployment aus.
        Berücksichtigt Traffic-Splitting für neue/unsichere Varianten und Blacklist.
        """
        self._update_blacklist() # Vor jeder Auswahl Blacklist aktualisieren

        available_for_bandit = list(self.active_variants - self.blacklisted_variants)
        
        # Wenn keine Varianten verfügbar sind, immer Basis-Variante zurückgeben
        if not available_for_bandit:
            logger.warning("Keine aktiven Varianten verfügbar, Fallback auf Basis-Variante.")
            record_policy_pull("TOM", "general", self.config.base_variant)
            return self.config.base_variant

        # Priorisiere neue/unsichere Varianten für Traffic-Split
        new_variants = [v for v in available_for_bandit if self._is_new_variant(v)]
        uncertain_variants = [v for v in available_for_bandit if self._is_uncertain_variant(v) and v not in new_variants]
        
        selected_variant = None

        # Traffic-Split für neue Varianten
        if new_variants and _random.random() < self.config.traffic_split_new:
            selected_variant = _random.choice(new_variants)
            logger.debug(f"Deployment Guard wählt neue Variante (Traffic Split): {selected_variant}")
        
        # Traffic-Split für unsichere Varianten (wenn keine neue gewählt wurde)
        if not selected_variant and uncertain_variants and _random.random() < self.config.traffic_split_uncertain:
            selected_variant = _random.choice(uncertain_variants)
            logger.debug(f"Deployment Guard wählt unsichere Variante (Traffic Split): {selected_variant}")

        # Wenn kein Traffic-Split zutrifft, oder keine speziellen Varianten, nutze Bandit
        if not selected_variant:
            # Bandit wählt nur aus den aktiven, nicht blacklisted Varianten
            self.bandit.state.variants = {k: v for k, v in self.bandit.state.variants.items() if k in available_for_bandit}
            selected_variant = self.bandit.select(context)
            if not selected_variant: # Fallback, falls Bandit nichts zurückgibt
                selected_variant = self.config.base_variant
            logger.debug(f"Deployment Guard wählt Variante über Bandit: {selected_variant}")

        record_policy_pull("TOM", "general", selected_variant)
        return selected_variant

    def add_variant_to_deployment(self, variant_id: str) -> bool:
        """Fügt eine Variante zum aktiven Deployment hinzu."""
        if variant_id in self.blacklisted_variants:
            logger.warning(f"Variante '{variant_id}' ist blacklisted und kann nicht hinzugefügt werden.")
            return False
        if len(self.active_variants) >= self.config.max_active_variants + 1: # +1 für Basis-Variante
            logger.warning(f"Maximale Anzahl aktiver Varianten ({self.config.max_active_variants}) erreicht. Kann '{variant_id}' nicht hinzufügen.")
            return False
        
        self.active_variants.add(variant_id)
        self._save_state()
        logger.info(f"Variante '{variant_id}' zum Deployment hinzugefügt.")
        return True

    def remove_variant_from_deployment(self, variant_id: str) -> bool:
        """Entfernt eine Variante aus dem aktiven Deployment."""
        if variant_id == self.config.base_variant:
            logger.warning("Basis-Variante kann nicht aus dem Deployment entfernt werden.")
            return False
        if variant_id in self.active_variants:
            self.active_variants.remove(variant_id)
            self._save_state()
            logger.info(f"Variante '{variant_id}' aus dem Deployment entfernt.")
            return True
        logger.warning(f"Variante '{variant_id}' ist nicht im aktiven Deployment.")
        return False

    def get_deployment_status(self) -> Dict[str, Any]:
        """Gibt den aktuellen Status des Deployments zurück."""
        return {
            'active_variants': sorted(list(self.active_variants)),
            'blacklisted_variants': sorted(list(self.blacklisted_variants)),
            'base_variant': self.config.base_variant,
            'last_update': self.last_update.isoformat(),
            'config': self.config.model_dump()
        }

    def get_variant_health(self, variant_id: str) -> Dict[str, Any]:
        """Gibt Gesundheitsinformationen für eine spezifische Variante zurück."""
        all_stats = get_policy_stats()
        stats = all_stats.get(variant_id, {})
        is_active = variant_id in self.active_variants
        is_blacklisted = variant_id in self.blacklisted_variants
        is_new = self._is_new_variant(variant_id)
        is_uncertain = self._is_uncertain_variant(variant_id)

        return {
            'id': variant_id,
            'is_active': is_active,
            'is_blacklisted': is_blacklisted,
            'is_new': is_new,
            'is_uncertain': is_uncertain,
            'stats': stats
        }

# Convenience-Funktionen
_deploy_guard: Optional[DeployGuardFull] = None

def _get_deploy_guard() -> DeployGuardFull:
    global _deploy_guard
    if _deploy_guard is None:
        _deploy_guard = DeployGuardFull()
    return _deploy_guard

def select_variant_for_deployment(context: Optional[Dict[str, Any]] = None) -> str:
    return _get_deploy_guard().select_variant_for_deployment(context)

def add_variant_to_deployment(variant_id: str) -> bool:
    return _get_deploy_guard().add_variant_to_deployment(variant_id)

def remove_variant_from_deployment(variant_id: str) -> bool:
    return _get_deploy_guard().remove_variant_from_deployment(variant_id)

def get_deployment_status() -> Dict[str, Any]:
    return _get_deploy_guard().get_deployment_status()

def get_variant_health(variant_id: str) -> Dict[str, Any]:
    return _get_deploy_guard().get_variant_health(variant_id)