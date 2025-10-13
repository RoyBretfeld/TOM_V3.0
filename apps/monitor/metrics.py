"""
TOM v3.0 - RL Metrics Exporter
Prometheus-Metriken für Reinforcement Learning System
"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Registry für RL-Metriken
rl_registry = CollectorRegistry()

# RL-spezifische Metriken
rl_feedback_total = Counter(
    'rl_feedback_total',
    'Total number of feedback events collected',
    ['policy_variant', 'profile', 'agent'],
    registry=rl_registry
)

rl_reward_histogram = Histogram(
    'rl_reward_distribution',
    'Distribution of reward values',
    ['policy_variant'],
    buckets=[-1.0, -0.5, -0.2, 0.0, 0.2, 0.5, 0.8, 1.0],
    registry=rl_registry
)

rl_user_rating_histogram = Histogram(
    'rl_user_rating_distribution',
    'Distribution of user ratings (1-5)',
    ['policy_variant'],
    buckets=[1, 2, 3, 4, 5],
    registry=rl_registry
)

rl_policy_pulls_total = Counter(
    'rl_policy_pulls_total',
    'Total number of policy pulls',
    ['policy_variant'],
    registry=rl_registry
)

rl_policy_success_rate = Gauge(
    'rl_policy_success_rate',
    'Success rate per policy variant',
    ['policy_variant'],
    registry=rl_registry
)

rl_bandit_exploration_rate = Gauge(
    'rl_bandit_exploration_rate',
    'Current exploration rate of bandit',
    registry=rl_registry
)

rl_active_variants = Gauge(
    'rl_active_variants_total',
    'Number of active policy variants',
    registry=rl_registry
)

rl_blacklisted_variants = Gauge(
    'rl_blacklisted_variants_total',
    'Number of blacklisted policy variants',
    registry=rl_registry
)

rl_session_duration_histogram = Histogram(
    'rl_session_duration_seconds',
    'Distribution of session durations',
    ['policy_variant'],
    buckets=[30, 60, 120, 180, 300, 600, 900],
    registry=rl_registry
)

rl_barge_in_total = Counter(
    'rl_barge_in_total',
    'Total number of barge-ins',
    ['policy_variant'],
    registry=rl_registry
)

rl_escalation_total = Counter(
    'rl_escalation_total',
    'Total number of escalations',
    ['policy_variant'],
    registry=rl_registry
)

class RLMetricsExporter:
    """Exportiert RL-Metriken nach Prometheus"""
    
    def __init__(self):
        self.last_update = datetime.now()
        
    def record_feedback(self, policy_variant: str, profile: str, agent: str = "TOM"):
        """Zeichnet Feedback-Event auf"""
        rl_feedback_total.labels(
            policy_variant=policy_variant,
            profile=profile,
            agent=agent
        ).inc()
        
    def record_reward(self, policy_variant: str, reward: float):
        """Zeichnet Reward-Wert auf"""
        rl_reward_histogram.labels(policy_variant=policy_variant).observe(reward)
        
    def record_user_rating(self, policy_variant: str, rating: int):
        """Zeichnet Benutzerbewertung auf"""
        if 1 <= rating <= 5:
            rl_user_rating_histogram.labels(policy_variant=policy_variant).observe(rating)
            
    def record_policy_pull(self, policy_variant: str):
        """Zeichnet Policy-Pull auf"""
        rl_policy_pulls_total.labels(policy_variant=policy_variant).inc()
        
    def update_success_rate(self, policy_variant: str, success_rate: float):
        """Aktualisiert Erfolgsrate"""
        rl_policy_success_rate.labels(policy_variant=policy_variant).set(success_rate)
        
    def update_exploration_rate(self, exploration_rate: float):
        """Aktualisiert Exploration-Rate"""
        rl_bandit_exploration_rate.set(exploration_rate)
        
    def update_active_variants(self, count: int):
        """Aktualisiert Anzahl aktiver Varianten"""
        rl_active_variants.set(count)
        
    def update_blacklisted_variants(self, count: int):
        """Aktualisiert Anzahl schwarzer Varianten"""
        rl_blacklisted_variants.set(count)
        
    def record_session_duration(self, policy_variant: str, duration_sec: float):
        """Zeichnet Session-Dauer auf"""
        rl_session_duration_histogram.labels(policy_variant=policy_variant).observe(duration_sec)
        
    def record_barge_in(self, policy_variant: str, count: int = 1):
        """Zeichnet Barge-Ins auf"""
        rl_barge_in_total.labels(policy_variant=policy_variant).inc(count)
        
    def record_escalation(self, policy_variant: str):
        """Zeichnet Eskalation auf"""
        rl_escalation_total.labels(policy_variant=policy_variant).inc()
        
    def get_metrics(self) -> str:
        """Gibt Prometheus-Metriken als String zurück"""
        return generate_latest(rl_registry).decode('utf-8')
        
    def get_metrics_dict(self) -> Dict[str, Any]:
        """Gibt Metriken als Dictionary zurück"""
        metrics_text = self.get_metrics()
        metrics_dict = {}
        
        for line in metrics_text.split('\n'):
            if line and not line.startswith('#'):
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_name = parts[0]
                    metric_value = float(parts[1])
                    metrics_dict[metric_name] = metric_value
                    
        return metrics_dict

# Convenience-Funktionen
_metrics_exporter: Optional[RLMetricsExporter] = None

def _get_metrics_exporter() -> RLMetricsExporter:
    global _metrics_exporter
    if _metrics_exporter is None:
        _metrics_exporter = RLMetricsExporter()
    return _metrics_exporter

def record_feedback(policy_variant: str, profile: str, agent: str = "TOM"):
    """Zeichnet Feedback-Event auf"""
    _get_metrics_exporter().record_feedback(policy_variant, profile, agent)

def record_reward(policy_variant: str, reward: float):
    """Zeichnet Reward-Wert auf"""
    _get_metrics_exporter().record_reward(policy_variant, reward)

def record_user_rating(policy_variant: str, rating: int):
    """Zeichnet Benutzerbewertung auf"""
    _get_metrics_exporter().record_user_rating(policy_variant, rating)

def record_policy_pull(policy_variant: str):
    """Zeichnet Policy-Pull auf"""
    _get_metrics_exporter().record_policy_pull(policy_variant)

def update_success_rate(policy_variant: str, success_rate: float):
    """Aktualisiert Erfolgsrate"""
    _get_metrics_exporter().update_success_rate(policy_variant, success_rate)

def update_exploration_rate(exploration_rate: float):
    """Aktualisiert Exploration-Rate"""
    _get_metrics_exporter().update_exploration_rate(exploration_rate)

def update_active_variants(count: int):
    """Aktualisiert Anzahl aktiver Varianten"""
    _get_metrics_exporter().update_active_variants(count)

def update_blacklisted_variants(count: int):
    """Aktualisiert Anzahl schwarzer Varianten"""
    _get_metrics_exporter().update_blacklisted_variants(count)

def record_session_duration(policy_variant: str, duration_sec: float):
    """Zeichnet Session-Dauer auf"""
    _get_metrics_exporter().record_session_duration(policy_variant, duration_sec)

def record_barge_in(policy_variant: str, count: int = 1):
    """Zeichnet Barge-Ins auf"""
    _get_metrics_exporter().record_barge_in(policy_variant, count)

def record_escalation(policy_variant: str):
    """Zeichnet Eskalation auf"""
    _get_metrics_exporter().record_escalation(policy_variant)

def get_metrics() -> str:
    """Gibt Prometheus-Metriken als String zurück"""
    return _get_metrics_exporter().get_metrics()

def get_metrics_dict() -> Dict[str, Any]:
    """Gibt Metriken als Dictionary zurück"""
    return _get_metrics_exporter().get_metrics_dict()
