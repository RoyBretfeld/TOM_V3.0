"""
TOM v3.0 - Prometheus Metrics Exporter
Erweitert um Gateway/Realtime Kennzahlen
"""

from datetime import datetime
import logging
import socketserver
import threading
import time
from typing import Any, Dict, Optional
from wsgiref.simple_server import WSGIServer, make_server

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    make_wsgi_app,
)

logger = logging.getLogger(__name__)

# Eigene Registry, damit wir mehrere Apps parallel fahren können
rl_registry = CollectorRegistry()

# Basis-Metriken -------------------------------------------------------------

tom_calls_active = Gauge(
    "tom_calls_active",
    "Number of active realtime call sessions",
    registry=rl_registry,
)

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

# ToolHub-Metriken
tom_tool_calls_total = Counter(
    'tom_tool_calls_total',
    'Total number of tool calls',
    ['tool', 'source'],
    registry=rl_registry
)

tom_tool_latency_ms = Histogram(
    'tom_tool_latency_ms',
    'Tool call latency in milliseconds',
    ['tool', 'source'],
    buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
    registry=rl_registry
)

tom_tool_calls_failed_total = Counter(
    'tom_tool_calls_failed_total',
    'Total number of failed tool calls',
    ['tool', 'source'],
    registry=rl_registry
)

# Pipeline-Metriken (alt) wurden entfernt und durch Realtime-spezifische Kennzahlen ersetzt

# Telefonie-Metriken
tom_telephony_active_calls_total = Gauge(
    'tom_telephony_active_calls_total',
    'Number of active calls',
    registry=rl_registry
)

tom_telephony_calls_total = Counter(
    'tom_telephony_calls_total',
    'Total number of calls',
    registry=rl_registry
)

tom_telephony_calls_failed_total = Counter(
    'tom_telephony_calls_failed_total',
    'Total number of failed calls',
    registry=rl_registry
)

tom_telephony_call_duration_seconds = Histogram(
    'tom_telephony_call_duration_seconds',
    'Call duration distribution',
    buckets=[10, 30, 60, 120, 300, 600, 900, 1800],
    registry=rl_registry
)

tom_telephony_barge_in_latency_seconds = Histogram(
    'tom_telephony_barge_in_latency_seconds',
    'Barge-in latency',
    registry=rl_registry
)

tom_ws_gateway_http_responses_total = Counter(
    'tom_ws_gateway_http_responses_total',
    'HTTP response codes served by the realtime gateway',
    ['code'],
    registry=rl_registry,
)

tom_ws_gateway_rate_limit_total = Counter(
    'tom_ws_gateway_rate_limit_total',
    'Rate limit hits on the WebSocket gateway',
    ['type'],
    registry=rl_registry
)

tom_audio_frames_sent_total = Counter(
    'tom_audio_frames_sent_total',
    'Audio frames forwarded to the realtime backend',
    registry=rl_registry,
)

tom_audio_frames_dropped_total = Counter(
    'tom_audio_frames_dropped_total',
    'Audio frames dropped due to backpressure',
    registry=rl_registry,
)

tom_ws_backpressure_events_total = Counter(
    'tom_ws_backpressure_events_total',
    'Total number of backpressure events in the gateway',
    registry=rl_registry,
)

tom_synth_call_last_success_timestamp_seconds = Gauge(
    'tom_synth_call_last_success_timestamp_seconds',
    'Unix timestamp of the last successful synthetic call',
    registry=rl_registry,
)

tom_ivr_consent_given_total = Counter(
    'tom_ivr_consent_given_total',
    'Number of callers who gave consent for recording',
    ['skill'],
    registry=rl_registry
)

tom_cli_rewrite_total = Counter(
    'tom_cli_rewrite_total',
    'Total number of CLI hashes generated',
    registry=rl_registry
)

tom_blocked_dial_attempts_total = Counter(
    'tom_blocked_dial_attempts_total',
    'Blocked outbound dial attempts',
    ['reason'],
    registry=rl_registry
)

# Error-Metriken
tom_errors_total = Counter(
    'tom_errors_total',
    'Total number of errors',
    ['component'],
    registry=rl_registry
)

# Realtime-Backend-Metriken
tom_realtime_backend = Gauge(
    'tom_realtime_backend',
    'Active Realtime backend (provider or local)',
    ['backend'],
    registry=rl_registry
)

tom_provider_failover_total = Counter(
    'tom_provider_failover_total',
    'Total number of provider failovers to local',
    registry=rl_registry
)

tom_realtime_e2e_ms = Histogram(
    'tom_realtime_e2e_ms',
    'Realtime end-to-end latency in milliseconds',
    buckets=[50, 100, 150, 200, 300, 500, 800, 1200, 2000],
    registry=rl_registry,
)

tom_stage_latency_ms = Histogram(
    'tom_stage_latency_ms',
    'Stage latency (ms) per component',
    ['stage'],
    buckets=[10, 20, 40, 80, 120, 200, 300, 500],
    registry=rl_registry,
)

# Globale Metriken-Instanz für einfachen Zugriff
class Metrics:
    """Zentrale Metriken-Klasse"""
    
    def __init__(self):
        self.tom_calls_active = tom_calls_active
        self.tom_realtime_e2e_ms = tom_realtime_e2e_ms
        self.tom_stage_latency_ms = tom_stage_latency_ms
        self.tom_ws_gateway_http_responses_total = tom_ws_gateway_http_responses_total
        self.tom_audio_frames_sent_total = tom_audio_frames_sent_total
        self.tom_audio_frames_dropped_total = tom_audio_frames_dropped_total
        self.tom_ws_backpressure_events_total = tom_ws_backpressure_events_total
        self.tom_synth_call_last_success_timestamp_seconds = (
            tom_synth_call_last_success_timestamp_seconds
        )
        self.tom_ws_gateway_rate_limit_total = tom_ws_gateway_rate_limit_total
        self.tom_tool_calls_total = tom_tool_calls_total
        self.tom_tool_latency_ms = tom_tool_latency_ms
        self.tom_tool_calls_failed_total = tom_tool_calls_failed_total
        self.tom_telephony_active_calls_total = tom_telephony_active_calls_total
        self.tom_telephony_calls_total = tom_telephony_calls_total
        self.tom_telephony_calls_failed_total = tom_telephony_calls_failed_total
        self.tom_telephony_call_duration_seconds = tom_telephony_call_duration_seconds
        self.tom_telephony_barge_in_latency_seconds = tom_telephony_barge_in_latency_seconds
        self.tom_errors_total = tom_errors_total
        self.tom_realtime_backend = tom_realtime_backend
        self.tom_provider_failover_total = tom_provider_failover_total
        self.tom_ivr_consent_given_total = tom_ivr_consent_given_total
        self.tom_cli_rewrite_total = tom_cli_rewrite_total
        self.tom_blocked_dial_attempts_total = tom_blocked_dial_attempts_total


# Globale Metriken-Instanz
metrics = Metrics()

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


class MetricsWSGIApp:
    """Einfache WSGI-App für /metrics und Admin-Endpunkte."""

    def __init__(self, admin_token: Optional[str] = None):
        self._prom_app = make_wsgi_app(rl_registry)
        self._admin_token = admin_token

    def __call__(self, environ, start_response):
        path = environ.get("PATH_INFO", "")
        method = environ.get("REQUEST_METHOD", "GET").upper()

        if path == "/metrics":
            return self._prom_app(environ, start_response)

        if path == "/metrics/synth" and method in {"POST", "PUT"}:
            if self._admin_token:
                auth = environ.get("HTTP_AUTHORIZATION", "")
                if not auth.lower().startswith("bearer ") or auth.split(" ", 1)[1] != self._admin_token:
                    start_response("401 Unauthorized", [("Content-Type", "text/plain")])
                    return [b"unauthorized"]
            metrics.set_synthetic_success()
            start_response("204 No Content", [])
            return [b""]

        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"not found"]


class ThreadedWSGIServer(socketserver.ThreadingMixIn, WSGIServer):
    daemon_threads = True


def start_metrics_server(host: str = "0.0.0.0", port: int = 9100, admin_token: Optional[str] = None) -> None:
    """Startet den Prometheus-Metrik-Server in einem Hintergrundthread."""

    app = MetricsWSGIApp(admin_token=admin_token)

    def _run() -> None:
        with make_server(host, port, app, ThreadedWSGIServer) as httpd:
            logger.info("Metrics server running on http://%s:%s/metrics", host, port)
            httpd.serve_forever()

    thread = threading.Thread(target=_run, name="metrics-server", daemon=True)
    thread.start()
