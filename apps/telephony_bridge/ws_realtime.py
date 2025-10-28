#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Secure WebSocket Gateway für Realtime-Pipeline
Echte Provider-Sessions ohne Mocks
"""

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs

import jwt
import redis
import websockets
from pydantic import BaseModel, ValidationError
from websockets.server import WebSocketServerProtocol

# Lokale Imports
from apps.dispatcher.rt_fsm import RealtimeFSM
from apps.monitor.metrics import metrics
from apps.realtime.provider_realtime import RealtimeProvider
from apps.realtime.tts_piper import PiperTTSRealtime
from apps.security.phone_hash import PhoneHashConfigError, hash_phone_number, mask_number
from apps.telephony_bridge.audio_recorder import audio_recorder

logger = logging.getLogger(__name__)

# Konfiguration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key')
JWT_AUDIENCE = os.getenv('JWT_AUDIENCE', 'tom_ws_gateway')
JWT_ISSUER = os.getenv('JWT_ISSUER', 'tom_control_plane')
JWT_MAX_TTL_SECONDS = int(os.getenv('JWT_MAX_TTL_SECONDS', '60'))
REALTIME_WS_URL = os.getenv('REALTIME_WS_URL', 'wss://api.realtime.com/v1/stream')
REALTIME_API_KEY = os.getenv('REALTIME_API_KEY')
DEV_ALLOW_NO_JWT = os.getenv('DEV_ALLOW_NO_JWT', 'false').lower() == 'true'

# Allowlists & Security
WS_GATEWAY_IP_ALLOWLIST = {
    ip.strip() for ip in os.getenv('WS_GATEWAY_IP_ALLOWLIST', '').split(',') if ip.strip()
}
WS_GATEWAY_ORIGIN_ALLOWLIST = {
    origin.strip() for origin in os.getenv('WS_GATEWAY_ORIGIN_ALLOWLIST', '').split(',') if origin.strip()
}

# Rate Limiting
RATE_LIMIT_MSGS_PER_SEC = int(os.getenv('RATE_LIMIT_MSGS_PER_SEC', '120'))
RATE_LIMIT_WINDOW_SEC = 1
RATE_LIMIT_BYTES_PER_SEC = int(os.getenv('RATE_LIMIT_BYTES_PER_SEC', str(256 * 1024)))  # 256 KB/s
RATE_LIMIT_CONN_PER_MIN = int(os.getenv('RATE_LIMIT_CONN_PER_MIN', '30'))
MAX_FRAME_SIZE = 64 * 1024  # 64KB
RETRY_AFTER_SECONDS = float(os.getenv('RATE_LIMIT_RETRY_AFTER', '1.0'))
MAX_AUDIO_BUFFER_SIZE = int(os.getenv('WS_MAX_AUDIO_BUFFER', '50'))

# Pydantic Models
class AudioChunkEvent(BaseModel):
    type: str = "audio_chunk"
    audio: str  # base64 encoded PCM16/16k
    timestamp: float
    audio_length: int

class BargeInEvent(BaseModel):
    type: str = "barge_in"
    timestamp: float

class StopEvent(BaseModel):
    type: str = "stop"
    timestamp: float

class PingEvent(BaseModel):
    type: str = "ping"
    timestamp: float

class RealtimeWSGateway:
    """Secure WebSocket Gateway für Realtime-Pipeline"""
    
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        self.active_sessions: Dict[str, 'Session'] = {}
        self.rate_limits: Dict[str, deque] = defaultdict(lambda: deque())
        self.rate_limit_bytes: Dict[str, deque] = defaultdict(lambda: deque())
        self.connection_attempts: Dict[str, deque] = defaultdict(lambda: deque())
        self.provider = RealtimeProvider()
        self.pipert_tts = PiperTTSRealtime()
        self.fsm = RealtimeFSM()
        self.metrics = metrics
        
    def _validate_jwt(self, token: str, call_id: str) -> bool:
        """JWT validieren mit Replay-Schutz"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            # Basis-Validierung
            if payload.get('iss') != JWT_ISSUER:
                return False
            audience = payload.get('aud')
            if isinstance(audience, (list, tuple, set)):
                if JWT_AUDIENCE not in audience:
                    return False
            elif audience != JWT_AUDIENCE:
                return False
            if payload.get('call_id') != call_id:
                return False
            if payload.get('exp', 0) < time.time():
                return False
            iat = payload.get('iat')
            exp = payload.get('exp')
            if iat and exp and (exp - iat) > JWT_MAX_TTL_SECONDS:
                return False
            if iat and (time.time() - iat) > JWT_MAX_TTL_SECONDS:
                return False
            
            # Replay-Schutz via Redis
            nonce = payload.get('nonce')
            if not nonce:
                return False
                
            # SETNX für atomare Operation
            key = f"jwt_nonce:{nonce}"
            if not self.redis_client.set(key, "1", nx=True, ex=120):
                logger.warning(f"JWT Replay detected: {nonce}")
                return False
                
            return True
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return False

    def _check_origin(self, websocket: WebSocketServerProtocol) -> bool:
        origin = websocket.request_headers.get('Origin')
        if not WS_GATEWAY_ORIGIN_ALLOWLIST:
            return True
        return origin in WS_GATEWAY_ORIGIN_ALLOWLIST

    def _check_ip_allowlist(self, client_ip: str) -> bool:
        if not WS_GATEWAY_IP_ALLOWLIST:
            return True
        return client_ip in WS_GATEWAY_IP_ALLOWLIST

    def _record_http_response(self, code: int) -> None:
        self.metrics.tom_ws_gateway_http_responses_total.labels(code=str(code)).inc()

    def _record_rate_limit(self, limit_type: str) -> None:
        self.metrics.tom_ws_gateway_rate_limit_total.labels(type=limit_type).inc()

    def _check_connection_rate(self, client_ip: str) -> bool:
        now = time.time()
        window_start = now - 60
        attempts = self.connection_attempts[client_ip]
        while attempts and attempts[0] < window_start:
            attempts.popleft()

        if len(attempts) >= RATE_LIMIT_CONN_PER_MIN:
            return False

        attempts.append(now)
        return True
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Rate Limiting: 120 msg/s pro Verbindung"""
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SEC
        
        # Alte Einträge entfernen
        while self.rate_limits[client_id] and self.rate_limits[client_id][0] < window_start:
            self.rate_limits[client_id].popleft()
        
        # Prüfen ob Limit überschritten
        if len(self.rate_limits[client_id]) >= RATE_LIMIT_MSGS_PER_SEC:
            return False
            
        # Neuen Eintrag hinzufügen
        self.rate_limits[client_id].append(now)
        return True

    def _check_byte_limit(self, client_id: str, message_size: int) -> bool:
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SEC
        entries = self.rate_limit_bytes[client_id]

        while entries and entries[0][0] < window_start:
            entries.popleft()

        current_bytes = sum(size for _, size in entries)
        if current_bytes + message_size > RATE_LIMIT_BYTES_PER_SEC:
            return False

        entries.append((now, message_size))
        return True
    
    def _validate_event(self, data: dict) -> Optional[BaseModel]:
        """Pydantic-Validation für Events"""
        event_type = data.get('type')
        
        try:
            if event_type == 'audio_chunk':
                return AudioChunkEvent(**data)
            elif event_type == 'barge_in':
                return BargeInEvent(**data)
            elif event_type == 'stop':
                return StopEvent(**data)
            elif event_type == 'ping':
                return PingEvent(**data)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return None
        except ValidationError as e:
            logger.warning(f"Event validation failed: {e}")
            return None
    
    async def handle_client(self, websocket: WebSocketServerProtocol, path: str):
        """Haupt-Handler für Client-Verbindungen"""
        parsed_path = urlparse(path)
        query = parse_qs(parsed_path.query)
        raw_call_id = query.get('call_id', [parsed_path.path.rstrip('/').split('/')[-1]])[0]
        raw_cli = query.get('cli', [''])[0]
        skill = (query.get('skill', ['default'])[0] or 'default').lower()
        call_id = raw_call_id or str(uuid.uuid4())
        remote = websocket.remote_address or ('0.0.0.0', 0)
        client_ip = remote[0]
        client_id = f"{client_ip}:{remote[1]}"

        cli_hash = None
        masked_cli = None
        if raw_cli:
            try:
                phone_hash = hash_phone_number(raw_cli)
                cli_hash = phone_hash.value
                masked_cli = mask_number(raw_cli)
                self.metrics.tom_cli_rewrite_total.inc()
            except PhoneHashConfigError as exc:
                masked_cli = mask_number(raw_cli)
                logger.warning(f'CLI hashing failed for call {call_id}: {exc}')

        if not self._check_ip_allowlist(client_ip):
            logger.warning(f'Connection rejected (IP not allowed): {client_ip}')
            self.metrics.tom_blocked_dial_attempts_total.labels(reason='ip_allowlist').inc()
            self._record_http_response(403)
            await websocket.close(code=1008, reason='IP not allowed')
            return

        if not self._check_origin(websocket):
            origin = websocket.request_headers.get('Origin')
            logger.warning(f'Connection rejected (Origin not allowed): {origin}')
            self.metrics.tom_blocked_dial_attempts_total.labels(reason='origin').inc()
            self._record_http_response(403)
            await websocket.close(code=1008, reason='Origin not allowed')
            return

        if not self._check_connection_rate(client_ip):
            logger.warning(f'Connection rate limit hit for {client_ip}')
            self.metrics.tom_blocked_dial_attempts_total.labels(reason='conn_rate').inc()
            self._record_http_response(429)
            self._record_rate_limit('connections')
            await websocket.close(code=1013, reason='Connection rate limited')
            return

        logger.info(f'Client connected: {client_id}, Call-ID: {call_id}, CLI={masked_cli or "n/a"}, skill={skill}')
        self.metrics.tom_calls_active.inc()
        self.metrics.tom_telephony_active_calls_total.inc()
        self.metrics.tom_ivr_consent_given_total.labels(skill=skill).inc()
        self._record_http_response(101)
        
        # Audio-Recording starten (falls aktiviert)
        recording_sink = audio_recorder.start_recording(call_id)
        
        try:
            # JWT-Validierung (außer DEV-Modus)
            if not DEV_ALLOW_NO_JWT:
                # Erste Nachricht sollte JWT enthalten
                auth_message = await websocket.recv()
                auth_data = json.loads(auth_message)
                jwt_token = auth_data.get('jwt')
                
                if not jwt_token or not self._validate_jwt(jwt_token, call_id):
                    self._record_http_response(401)
                    await websocket.send(json.dumps({
                        'type': 'auth_error',
                        'message': 'Invalid or missing JWT token'
                    }))
                    await websocket.close(code=1008, reason='Authentication failed')
                    return
            
            # Session erstellen
            session = Session(call_id, websocket, self, cli_hash=cli_hash, skill=skill)
            self.active_sessions[call_id] = session
            
            # Provider-Session öffnen
            await session.open_provider_session()
            
            # Connected-Event senden
            await websocket.send(json.dumps({
                'type': 'connected',
                'call_id': call_id,
                'timestamp': datetime.now().isoformat(),
                'config': {
                    'stt_mode': os.getenv('REALTIME_STT', 'provider'),
                    'llm_mode': os.getenv('REALTIME_LLM', 'provider'),
                    'tts_mode': os.getenv('REALTIME_TTS', 'provider')
                }
            }))
            
            # Event-Loop
            async for message in websocket:
                try:
                    # Rate Limiting
                    if not self._check_rate_limit(client_id):
                        self._record_rate_limit('messages_per_sec')
                        await websocket.send(json.dumps({
                            'type': 'rate_limit_exceeded',
                            'message': 'Too many messages per second',
                            'retry_after': RETRY_AFTER_SECONDS
                        }))
                        await asyncio.sleep(RETRY_AFTER_SECONDS)
                        continue
                    
                    # Frame-Size Check
                    if len(message) > MAX_FRAME_SIZE:
                        logger.warning(f"Frame too large: {len(message)} bytes")
                        self._record_rate_limit('frame_size')
                        continue
                    
                    if not self._check_byte_limit(client_id, len(message)):
                        logger.warning(f"Byte limit exceeded for {client_id}")
                        self._record_rate_limit('bytes_per_sec')
                        await websocket.send(json.dumps({
                            'type': 'rate_limit_exceeded',
                            'message': 'Too many bytes per second',
                            'retry_after': RETRY_AFTER_SECONDS
                        }))
                        await asyncio.sleep(RETRY_AFTER_SECONDS)
                        continue
                    
                    # Event validieren
                    data = json.loads(message)
                    validated_event = self._validate_event(data)
                    
                    if not validated_event:
                        continue
                    
                    # Audio-Chunk aufzeichnen (falls Recording aktiv)
                    if validated_event.type == 'audio_chunk' and recording_sink:
                        try:
                            audio_bytes = base64.b64decode(validated_event.audio)
                            recording_sink.write_pcm16_16k(audio_bytes)
                        except Exception as e:
                            logger.warning(f"Fehler beim Audio-Recording: {e}")
                    
                    # Event verarbeiten
                    await session.handle_event(validated_event)
                    
                except json.JSONDecodeError as e:
                    logger.warning(f'JSON decode error: {e}')
                except Exception as e:
                    logger.error(f'Message processing error: {e}')
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f'Client disconnected: {client_id}')
        except Exception as e:
            logger.error(f'Connection error: {e}')
        finally:
            # Session cleanup
            if call_id in self.active_sessions:
                await self.active_sessions[call_id].close()
                del self.active_sessions[call_id]
            
            # Rate limit cleanup
            if client_id in self.rate_limits:
                del self.rate_limits[client_id]
            
            # Audio-Recording beenden
            if recording_sink:
                audio_recorder.stop_recording(call_id)
                logger.info(f"Audio-Recording beendet für {call_id}")
            
            # Cleanup alter Aufnahmen
            audio_recorder.cleanup_old_recordings()

            try:
                self.metrics.tom_calls_active.dec()
                self.metrics.tom_telephony_active_calls_total.dec()
            except ValueError:
                # Gauge kann nicht unter 0 fallen, logge nur für Debug
                logger.debug("Attempted to decrement calls gauge below zero")


class Session:
    """Einzelne Client-Session mit Provider-Verbindung"""
    
    def __init__(
        self,
        call_id: str,
        websocket: WebSocketServerProtocol,
        gateway: RealtimeWSGateway,
        *,
        cli_hash: Optional[str] = None,
        skill: str = 'default'
    ):
        self.call_id = call_id
        self.websocket = websocket
        self.gateway = gateway
        self.cli_hash = cli_hash
        self.skill = skill
        self.provider_session = None
        self.fsm_state = "LISTENING"
        self.audio_buffer = []
        self.last_audio_time = 0
        
    async def open_provider_session(self):
        """Provider-Session öffnen"""
        try:
            await self.gateway.provider.open()
            self.provider_session = self.gateway.provider
            logger.info(f"Provider session opened for call {self.call_id}")
        except Exception as e:
            logger.error(f"Failed to open provider session: {e}")
            await self.websocket.send(json.dumps({
                'type': 'provider_error',
                'message': 'Failed to connect to provider'
            }))
    
    async def handle_event(self, event: BaseModel):
        """Event verarbeiten"""
        if event.type == 'audio_chunk':
            await self.handle_audio_chunk(event)
        elif event.type == 'barge_in':
            await self.handle_barge_in(event)
        elif event.type == 'stop':
            await self.handle_stop(event)
        elif event.type == 'ping':
            await self.handle_ping(event)
    
    async def handle_audio_chunk(self, event: AudioChunkEvent):
        """Audio-Chunk an Provider weiterleiten"""
        if not self.provider_session:
            return
            
        try:
            # Base64 dekodieren
            audio_bytes = base64.b64decode(event.audio)

            # Backpressure überwachen (Dropping ältester Einträge)
            self.audio_buffer.append(event.timestamp)
            if len(self.audio_buffer) > MAX_AUDIO_BUFFER_SIZE:
                self.audio_buffer.pop(0)
                self.gateway.metrics.tom_pipeline_backpressure_total.inc()
                logger.debug(f"Backpressure triggered for call {self.call_id} (buffer>{MAX_AUDIO_BUFFER_SIZE})")

            if self.last_audio_time:
                jitter = abs(event.timestamp - self.last_audio_time)
                if jitter > 0.2:
                    logger.debug(f"Jitter detected for call {self.call_id}: {jitter:.3f}s")
            self.last_audio_time = event.timestamp
            
            # An Provider senden
            await self.provider_session.send_audio(audio_bytes, event.timestamp)
            
            # FSM-Update
            await self.gateway.fsm.process_audio_chunk(self.call_id, event)
            
            # Downstream-Events lesen
            await self.process_provider_events()
            
        except Exception as e:
            logger.error(f"Audio chunk processing error: {e}")
    
    async def handle_barge_in(self, event: BargeInEvent):
        """Barge-In: Provider und lokales TTS stoppen"""
        try:
            # Provider cancel
            if self.provider_session:
                await self.provider_session.cancel()
            
            # Lokales TTS stoppen
            await self.gateway.pipert_tts.stop()
            
            # FSM-Update
            await self.gateway.fsm.process_barge_in(self.call_id, event)
            
            # Barge-In bestätigen
            await self.websocket.send(json.dumps({
                'type': 'barge_in_ack',
                'timestamp': datetime.now().isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Barge-in processing error: {e}")
    
    async def handle_stop(self, event: StopEvent):
        """Stop: Session beenden"""
        await self.close()
    
    async def handle_ping(self, event: PingEvent):
        """Ping: Pong zurücksenden"""
        await self.websocket.send(json.dumps({
            'type': 'pong',
            'timestamp': datetime.now().isoformat(),
            'latency_ms': (time.time() - event.timestamp) * 1000
        }))
    
    async def process_provider_events(self):
        """Provider-Events lesen und weiterleiten"""
        if not self.provider_session:
            return
            
        try:
            async for event in self.provider_session.recv():
                # Event an Client weiterleiten
                await self.websocket.send(json.dumps(event))
                
                # FSM-Update basierend auf Event-Typ
                if event.get('type') == 'stt_final':
                    await self.gateway.fsm.process_stt_final(self.call_id, event)
                elif event.get('type') == 'llm_token':
                    await self.gateway.fsm.process_llm_token(self.call_id, event)
                elif event.get('type') == 'tts_audio':
                    await self.gateway.fsm.process_tts_audio(self.call_id, event)
                
        except Exception as e:
            logger.error(f"Provider event processing error: {e}")
    
    async def close(self):
        """Session schließen"""
        try:
            if self.provider_session:
                await self.provider_session.close()
                self.provider_session = None
            
            if not self.websocket.closed:
                await self.websocket.close()
                
        except Exception as e:
            logger.error(f"Session close error: {e}")


async def main():
    """Hauptfunktion"""
    gateway = RealtimeWSGateway()
    
    logger.info('Starting TOM v3.0 Realtime WebSocket Gateway...')
    logger.info(f'Provider URL: {REALTIME_WS_URL}')
    logger.info(f'DEV mode: {DEV_ALLOW_NO_JWT}')
    
    # WebSocket Server starten
    start_server = websockets.serve(
        gateway.handle_client, 
        'localhost', 
        8081,
        subprotocols=['realtime-v1']
    )
    
    await start_server
    logger.info('Server running on ws://localhost:8081/ws/stream/{call_id}')
    
    # Forever loop
    await asyncio.Future()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())
