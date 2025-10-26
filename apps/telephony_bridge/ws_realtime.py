#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOM v3.0 - Secure WebSocket Gateway für Realtime-Pipeline
Echte Provider-Sessions ohne Mocks
"""

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
import websockets
from websockets.server import WebSocketServerProtocol
import redis
from pydantic import BaseModel, ValidationError
import jwt
from collections import defaultdict, deque

# Lokale Imports
from apps.realtime.provider_realtime import RealtimeProvider
from apps.realtime.tts_piper import PiperTTSRealtime
from apps.dispatcher.rt_fsm import RealtimeFSM
from apps.telephony_bridge.audio_recorder import audio_recorder

logger = logging.getLogger(__name__)

# Konfiguration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-key')
REALTIME_WS_URL = os.getenv('REALTIME_WS_URL', 'wss://api.realtime.com/v1/stream')
REALTIME_API_KEY = os.getenv('REALTIME_API_KEY')
DEV_ALLOW_NO_JWT = os.getenv('DEV_ALLOW_NO_JWT', 'false').lower() == 'true'

# Rate Limiting
RATE_LIMIT_MSGS_PER_SEC = 120
RATE_LIMIT_WINDOW_SEC = 1
MAX_FRAME_SIZE = 64 * 1024  # 64KB

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
        self.provider = RealtimeProvider()
        self.pipert_tts = PiperTTSRealtime()
        self.fsm = RealtimeFSM()
        
    def _validate_jwt(self, token: str, call_id: str) -> bool:
        """JWT validieren mit Replay-Schutz"""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
            
            # Basis-Validierung
            if payload.get('sub') != 'realtime_user':
                return False
            if payload.get('call_id') != call_id:
                return False
            if payload.get('exp', 0) < time.time():
                return False
            
            # Replay-Schutz via Redis
            nonce = payload.get('nonce')
            if not nonce:
                return False
                
            # SETNX für atomare Operation
            key = f"jwt_nonce:{nonce}"
            if not self.redis_client.set(key, "1", nx=True, ex=300):  # 5min TTL
                logger.warning(f"JWT Replay detected: {nonce}")
                return False
                
            return True
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            return False
    
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
        # Call-ID aus Path extrahieren
        call_id = path.split('/')[-1] if '/' in path else str(uuid.uuid4())
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        
        logger.info(f'Client connected: {client_id}, Call-ID: {call_id}')
        
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
                    await websocket.send(json.dumps({
                        'type': 'auth_error',
                        'message': 'Invalid or missing JWT token'
                    }))
                    await websocket.close(code=1008, reason='Authentication failed')
                    return
            
            # Session erstellen
            session = Session(call_id, websocket, self)
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
                        await websocket.send(json.dumps({
                            'type': 'rate_limit_exceeded',
                            'message': 'Too many messages per second'
                        }))
                        continue
                    
                    # Frame-Size Check
                    if len(message) > MAX_FRAME_SIZE:
                        logger.warning(f"Frame too large: {len(message)} bytes")
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


class Session:
    """Einzelne Client-Session mit Provider-Verbindung"""
    
    def __init__(self, call_id: str, websocket: WebSocketServerProtocol, gateway: RealtimeWSGateway):
        self.call_id = call_id
        self.websocket = websocket
        self.gateway = gateway
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
            import base64
            audio_bytes = base64.b64decode(event.audio)
            
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
