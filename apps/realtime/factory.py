"""
TOM v3.0 - RealtimeSession Factory mit Fallback-Logik
Provider → Local automatischer Failover
"""

import os
import logging
import asyncio
import time
from typing import Optional, AsyncIterator
from collections import deque

from .session import RealtimeSession, RealtimeBackend
from .local_realtime import LocalRealtimeSession
from .provider_realtime import RealtimeProvider
from apps.monitor.metrics import metrics

logger = logging.getLogger(__name__)


# Fallback-Parameter
FALLBACK_POLICY = os.getenv('FALLBACK_POLICY', 'provider_then_local')
FALLBACK_TRIGGER_MS = int(os.getenv('FALLBACK_TRIGGER_MS', '800'))
FALLBACK_ERROR_BURST = int(os.getenv('FALLBACK_ERROR_BURST', '3'))
FALLBACK_ERROR_WINDOW = int(os.getenv('FALLBACK_ERROR_WINDOW', '60'))

# Cooldown nach Fallback
FALLBACK_COOLDOWN_SEC = int(os.getenv('FALLBACK_COOLDOWN_SEC', '600'))

# Latency-Tracking
e2e_latency_buffer = deque(maxlen=100)  # Puffer für p95-Berechnung


def create_realtime_session(session_id: str) -> RealtimeSession:
    """Erstellt Realtime-Session basierend auf ENV-Konfiguration mit Fallback"""
    
    backend_type = os.getenv('REALTIME_BACKEND', 'local')
    allow_egress = os.getenv('ALLOW_EGRESS', 'false').lower() == 'true'
    fallback_policy = os.getenv('FALLBACK_POLICY', 'provider_then_local')
    
    # Prüfe ob Provider-Modus erlaubt ist
    if backend_type == 'provider' and not allow_egress:
        logger.warning("Provider backend requested but ALLOW_EGRESS=false, falling back to local")
        backend_type = 'local'
    
    # Session erstellen
    if backend_type == 'provider' and fallback_policy == 'provider_then_local':
        logger.info(f"Creating ProviderRealtimeSession with fallback for {session_id}")
        return ProviderRealtimeSessionWithFallback(session_id)
    elif backend_type == 'provider':
        logger.info(f"Creating ProviderRealtimeSession for {session_id}")
        return ProviderRealtimeSession(session_id)
    else:
        logger.info(f"Creating LocalRealtimeSession for {session_id}")
        return LocalRealtimeSession(session_id)


class ProviderRealtimeSessionWithFallback(LocalRealtimeSession):
    """Provider-Session mit automatischem Fallback auf Local"""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.provider = RealtimeProvider()
        self.fallback_session = None
        self.current_backend = 'provider'
        self.error_count = 0
        self.error_times = deque(maxlen=FALLBACK_ERROR_BURST)
        self.last_failover_time = 0
        self.e2e_latencies = deque(maxlen=50)
        
    async def open(self) -> None:
        """Provider-Session öffnen mit Fallback"""
        await super().open()
        
        try:
            await self.provider.open()
            logger.info(f"Provider session opened for {self.session_id}")
            
            # Metrik: Backend-Typ setzen
            metrics.tom_realtime_backend.labels(
                backend='provider'
            ).set(1)
            
        except Exception as e:
            logger.error(f"Failed to open provider session: {e}")
            # Fallback auf Local
            await self._failover_to_local()
            
    async def close(self) -> None:
        """Session schließen"""
        try:
            if self.provider:
                await self.provider.close()
        finally:
            if self.fallback_session:
                await self.fallback_session.close()
            await super().close()
            
    async def send_audio(self, audio_bytes: bytes, timestamp: float) -> None:
        """Audio senden mit automatischem Failover"""
        try:
            if self.current_backend == 'provider':
                await self.provider.send_audio(audio_bytes, timestamp)
            else:
                await self.fallback_session.send_audio(audio_bytes, timestamp)
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            await self._handle_error()
            
    async def cancel(self) -> None:
        """Abbrechen"""
        try:
            if self.current_backend == 'provider':
                await self.provider.cancel()
            else:
                await self.fallback_session.cancel()
        finally:
            await super().cancel()
            
    async def send_event(self, event: dict) -> None:
        """Event senden"""
        try:
            if self.current_backend == 'provider':
                await self.provider.send_event(event)
            else:
                await self.fallback_session.send_event(event)
        except Exception as e:
            logger.error(f"Error sending event: {e}")
            await self._handle_error()
            
    async def recv_events(self) -> AsyncIterator[dict]:
        """Events empfangen mit Fallback"""
        try:
            if self.current_backend == 'provider':
                async for event in self.provider.recv():
                    # Latenz messen
                    if event.get('type') == 'tts_audio':
                        await self._update_latency_metrics(event)
                    yield event
            else:
                async for event in self.fallback_session.recv_events():
                    if event.get('type') == 'tts_audio':
                        await self._update_latency_metrics(event)
                    yield event
        except Exception as e:
            logger.error(f"Error receiving events: {e}")
            await self._handle_error()
            # Fallback: lokale Events
            async for event in super().recv_events():
                yield event
    
    async def _handle_error(self):
        """Fehler behandeln und ggf. Failover auslösen"""
        self.error_count += 1
        self.error_times.append(time.time())
        
        # Prüfe ob Failover nötig ist
        recent_errors = sum(
            1 for t in self.error_times 
            if time.time() - t < FALLBACK_ERROR_WINDOW
        )
        
        if recent_errors >= FALLBACK_ERROR_BURST:
            logger.warning(f"Error burst detected ({recent_errors} errors in {FALLBACK_ERROR_WINDOW}s), failing over to local")
            metrics.tom_provider_failover_total.inc()
            await self._failover_to_local()
    
    async def _failover_to_local(self):
        """Wechselt auf lokale Session"""
        # Cooldown prüfen
        if time.time() - self.last_failover_time < FALLBACK_COOLDOWN_SEC:
            logger.info(f"Failover cooldown active (last: {self.last_failover_time})")
            return
        
        logger.info(f"Failing over to local session for {self.session_id}")
        
        try:
            # Provider schließen
            if self.provider:
                await self.provider.close()
        except Exception as e:
            logger.warning(f"Error closing provider: {e}")
        
        # Lokale Session erstellen
        self.fallback_session = LocalRealtimeSession(self.session_id)
        await self.fallback_session.open()
        
        # Backend wechseln
        self.current_backend = 'local'
        self.last_failover_time = time.time()
        
        # Metrik: Backend-Typ aktualisieren
        metrics.tom_realtime_backend.labels(backend='provider').set(0)
        metrics.tom_realtime_backend.labels(backend='local').set(1)
        
        logger.info(f"Successfully failed over to local for {self.session_id}")
    
    async def _update_latency_metrics(self, event: dict):
        """Aktualisiert E2E-Latenz-Metriken"""
        if 'timestamp' in event:
            latency = time.time() - event['timestamp']
            e2e_latency_buffer.append(latency)
            
            # p95 berechnen
            if len(e2e_latency_buffer) >= 10:
                sorted_latencies = sorted(e2e_latency_buffer)
                p95_idx = int(len(sorted_latencies) * 0.95)
                p95_latency = sorted_latencies[p95_idx]
                
                # Prüfe ob Failover nötig ist
                if p95_latency * 1000 > FALLBACK_TRIGGER_MS and self.current_backend == 'provider':
                    logger.warning(f"p95 latency {p95_latency*1000:.1f}ms exceeds threshold {FALLBACK_TRIGGER_MS}ms, triggering failover")
                    await self._failover_to_local()


class ProviderRealtimeSession(LocalRealtimeSession):
    """Provider-basierte Realtime-Session (Wrapping Provider)"""
    
    def __init__(self, session_id: str):
        super().__init__(session_id)
        self.provider = RealtimeProvider()
        
    async def open(self) -> None:
        """Provider-Session öffnen"""
        await super().open()
        
        try:
            await self.provider.open()
            logger.info(f"Provider session opened for {self.session_id}")
        except Exception as e:
            logger.error(f"Failed to open provider session: {e}")
            self.is_connected = False
            
    async def close(self) -> None:
        """Provider-Session schließen"""
        try:
            if self.provider:
                await self.provider.close()
        finally:
            await super().close()
            
    async def send_audio(self, audio_bytes: bytes, timestamp: float) -> None:
        """Audio an Provider senden"""
        try:
            await self.provider.send_audio(audio_bytes, timestamp)
        except Exception as e:
            logger.error(f"Error sending audio to provider: {e}")
            
    async def cancel(self) -> None:
        """Provider abbrechen"""
        try:
            await self.provider.cancel()
        finally:
            await super().cancel()
            
    async def send_event(self, event: dict) -> None:
        """Event an Provider senden"""
        try:
            await self.provider.send_event(event)
        except Exception as e:
            logger.error(f"Error sending event to provider: {e}")
            
    async def recv_events(self) -> 'AsyncIterator[dict]':
        """Events von Provider empfangen"""
        try:
            async for event in self.provider.recv():
                yield event
        except Exception as e:
            logger.error(f"Error receiving events from provider: {e}")
            await super().recv_events()  # Fallback zu lokaler Session

