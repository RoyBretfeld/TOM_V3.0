#!/usr/bin/env python3
"""
TOM v3.0 - Telephony Bridge WebSocket Server

Sicherer WebSocket-Server für Echtzeit-Audio-Kommunikation mit:
- JWT-basierter Authentifizierung
- Rate-Limiting (Token-Bucket Algorithmus)
- Pydantic-Validierung aller Events
- Replay-Schutz per Redis
- Strukturierte Logging mit UTF-8

CSB v1 Compliance:
- UTF-8 Encoding für alle Ausgaben
- Read-Only Schutz für Originaldaten
- Keine Debug-Logs über INFO hinaus
"""
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
import logging

import redis.asyncio as redis
from pydantic import BaseModel, ValidationError, Field
import jwt
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

# UTF-8 Encoding sicherstellen
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Konfiguration
class Config:
    """Konfiguration für Telephony Bridge"""
    REDIS_URL = "redis://localhost:6379/0"
    JWT_SECRET = "change_me_in_production"
    MAX_RATE_LIMIT = 120  # Messages per second
    MAX_CONNECTIONS = 1000
    HEARTBEAT_INTERVAL = 30  # Sekunden
    CALL_TIMEOUT = 300  # Sekunden
    DEV_ALLOW_NO_JWT = True  # DEV-Flag für JWT-Bypass

# Importiere Pydantic-Schemas
from .schemas import validate_event, create_mock_response, WSEvent

# Token-Bucket Rate Limiter
class TokenBucket:
    """Token-Bucket Rate Limiter für Verbindungslimitierung"""

    def __init__(self, rate: float, capacity: float):
        self.rate = rate  # Tokens pro Sekunde
        self.capacity = capacity  # Maximale Token-Anzahl
        self.tokens = capacity
        self.last_update = time.time()

    async def consume(self, tokens: int = 1) -> bool:
        """Verbraucht Tokens, gibt False zurück wenn Rate überschritten"""
        now = time.time()
        elapsed = now - self.last_update

        # Neue Tokens hinzufügen
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

class ConnectionManager:
    """Verwaltet WebSocket-Verbindungen"""

    def __init__(self):
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.call_connections: Dict[str, Set[str]] = {}  # call_id -> Set von connection_ids
        self.rate_limiters: Dict[str, TokenBucket] = {}
        self.last_activity: Dict[str, float] = {}

    async def add_connection(self, connection_id: str, websocket: WebSocketServerProtocol, call_id: str):
        """Fügt eine neue Verbindung hinzu"""
        self.connections[connection_id] = websocket
        self.call_connections.setdefault(call_id, set()).add(connection_id)
        self.rate_limiters[connection_id] = TokenBucket(Config.MAX_RATE_LIMIT, Config.MAX_RATE_LIMIT)
        self.last_activity[connection_id] = time.time()

    async def remove_connection(self, connection_id: str, call_id: str):
        """Entfernt eine Verbindung"""
        if connection_id in self.connections:
            del self.connections[connection_id]
        if connection_id in self.rate_limiters:
            del self.rate_limiters[connection_id]
        if connection_id in self.last_activity:
            del self.last_activity[connection_id]

        if call_id in self.call_connections:
            self.call_connections[call_id].discard(connection_id)
            if not self.call_connections[call_id]:
                del self.call_connections[call_id]

    async def check_rate_limit(self, connection_id: str) -> bool:
        """Prüft Rate-Limit für Verbindung"""
        if connection_id in self.rate_limiters:
            return await self.rate_limiters[connection_id].consume()
        return False

    def update_activity(self, connection_id: str):
        """Aktualisiert letzte Aktivität"""
        self.last_activity[connection_id] = time.time()

class TelephonyBridge:
    """Hauptklasse für den Telephony Bridge Server"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.connection_manager = ConnectionManager()
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        """Richtet sicheres Logging mit strukturiertem Format ein"""
        logger = logging.getLogger('telephony_bridge')
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)

            # Sicherheitskonformes Format ohne sensible Daten
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(call_id)s] %(message)s',
                encoding='utf-8'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    async def connect_redis(self):
        """Verbindet zu Redis"""
        try:
            self.redis_client = redis.from_url(
                Config.REDIS_URL,
                encoding='utf-8',
                decode_responses=True,
                max_connections=20
            )
            await self.redis_client.ping()
            self.logger.info("Redis-Verbindung erfolgreich hergestellt")
        except Exception as e:
            self.logger.error(f"Redis-Verbindungsfehler: {e}")
            raise

    async def authenticate_jwt(self, token: str, call_id: str) -> Dict[str, Any]:
        """Validiert JWT-Token mit erweiterten Sicherheitsprüfungen"""
        try:
            # Token dekodieren
            payload = jwt.decode(
                token,
                Config.JWT_SECRET,
                algorithms=['HS256'],
                options={"verify_exp": True, "verify_iat": True}
            )

            # Prüfen ob call_id übereinstimmt
            if payload.get('call_id') != call_id:
                self.logger.warning(f"Call ID mismatch: expected {call_id}, got {payload.get('call_id')}")
                raise jwt.InvalidTokenError("Call ID mismatch")

            # Replay-Schutz: Nonce einmalig verwenden
            nonce = payload.get('nonce')
            if nonce:
                nonce_key = f"nonce:{nonce}"
                if await self.redis_client.exists(nonce_key):
                    self.logger.warning(f"Replay attack detected for nonce: {nonce}")
                    raise jwt.InvalidTokenError("Nonce bereits verwendet")

                # Nonce mit TTL setzen (bis Token-Ablauf)
                exp_time = payload.get('exp', time.time() + 3600)
                ttl = max(1, int(exp_time - time.time()))
                await self.redis_client.setex(nonce_key, ttl, "used")

            self.logger.info(f"JWT authentication successful for call_id: {call_id}")
            return payload

        except jwt.ExpiredSignatureError:
            self.logger.warning(f"Expired token for call_id: {call_id}")
            raise jwt.InvalidTokenError("Token abgelaufen")
        except jwt.InvalidTokenError as e:
            self.logger.warning(f"JWT validation failed for call_id: {call_id} - {e}")
            raise jwt.InvalidTokenError(f"Token ungültig: {e}")
        except Exception as e:
            self.logger.error(f"Token verification error for call_id: {call_id}: {e}")
            raise jwt.InvalidTokenError(f"Token-Verifikation fehlgeschlagen: {e}")

    async def validate_event(self, data: Dict[str, Any]) -> WSEvent:
        """Validiert eingehende Event-Daten mit erweiterten Prüfungen"""
        try:
            return validate_event(data)
        except ValueError as e:
            self.logger.warning(f"Event-Validierung fehlgeschlagen: {e}")
            raise ValueError(f"Ungültiges Event-Format: {e}")
        except Exception as e:
            self.logger.warning(f"Event-Validierung Fehler: {e}")
            raise ValueError(f"Event validation error: {e}")

    async def handle_websocket(self, websocket: WebSocketServerProtocol, path: str):
        """Behandelt WebSocket-Verbindung mit erweiterter Authentifizierung"""
        connection_id = str(uuid.uuid4())
        call_id = None

        try:
            self.logger.info(f"[{connection_id}] Neue Verbindung - Path: {path}")

            # Path parsen: /ws/stream/{call_id}
            path_parts = path.strip('/').split('/')
            if len(path_parts) != 3 or path_parts[0] != 'ws' or path_parts[1] != 'stream':
                await websocket.send(json.dumps({
                    "error": "Ungültiger Pfad. Verwende /ws/stream/{call_id}",
                    "type": "error"
                }, ensure_ascii=False))
                self.logger.warning(f"[{connection_id}] Invalid path format")
                return

            call_id = path_parts[2]
            if not call_id or len(call_id) > 100:
                await websocket.send(json.dumps({
                    "error": "Ungültige Call-ID",
                    "type": "error"
                }, ensure_ascii=False))
                self.logger.warning(f"[{connection_id}] Invalid call_id: {call_id}")
                return

            # JWT-Authentifizierung
            try:
                # Token aus Header oder Query-Parameter extrahieren
                token = await self._extract_token(websocket, path)
                
                # DEV-Bypass für JWT
                if Config.DEV_ALLOW_NO_JWT and not token:
                    self.logger.info(f"[{connection_id}] DEV-Modus: JWT-Bypass aktiviert für Call {call_id}")
                    payload = {"call_id": call_id, "sub": "dev_user"}
                elif not token:
                    await websocket.send(json.dumps({
                        "error": "JWT token required",
                        "type": "error"
                    }, ensure_ascii=False))
                    self.logger.warning(f"[{connection_id}] No JWT token provided")
                    return
                else:
                    # Token validieren
                    payload = await self.authenticate_jwt(token, call_id)

                # Verbindung registrieren
                await self.connection_manager.add_connection(connection_id, websocket, call_id)
                self.logger.info(f"[{connection_id}] Verbindung registriert für Call {call_id}")

            except jwt.InvalidTokenError as e:
                await websocket.send(json.dumps({
                    "error": f"Authentication failed: {str(e)}",
                    "type": "error"
                }, ensure_ascii=False))
                self.logger.warning(f"[{connection_id}] Authentication failed: {e}")
                return
            except Exception as e:
                await websocket.send(json.dumps({
                    "error": "Internal authentication error",
                    "type": "error"
                }, ensure_ascii=False))
                self.logger.error(f"[{connection_id}] Authentication error: {e}")
                return

            # Heartbeat starten
            heartbeat_task = asyncio.create_task(self._heartbeat(websocket, connection_id))

            try:
                async for message in websocket:
                    await self._handle_message(websocket, connection_id, call_id, message)

            finally:
                heartbeat_task.cancel()

        except ConnectionClosed:
            self.logger.info(f"[{connection_id}] Verbindung geschlossen")
        except Exception as e:
            self.logger.error(f"[{connection_id}] Verbindungsfehler: {e}")
        finally:
            if call_id:
                await self.connection_manager.remove_connection(connection_id, call_id)
            self.logger.info(f"[{connection_id}] Verbindung beendet")

    async def _heartbeat(self, websocket: WebSocketServerProtocol, connection_id: str):
        """Sendet regelmäßige Heartbeats"""
        try:
            while True:
                await asyncio.sleep(Config.HEARTBEAT_INTERVAL)

                if connection_id not in self.connection_manager.connections:
                    break

                await websocket.send(json.dumps({
                    "type": "heartbeat",
                    "timestamp": time.time()
                }, ensure_ascii=False))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Heartbeat-Fehler für {connection_id}: {e}")

    async def _extract_token(self, websocket: WebSocketServerProtocol, path: str) -> Optional[str]:
        """Extrahiert JWT-Token aus Header oder Query-Parameter"""
        # Aus WebSocket-Subprotocol extrahieren (falls verfügbar)
        subprotocols = websocket.subprotocol
        if subprotocols and 'Bearer ' in subprotocols:
            return subprotocols.split('Bearer ')[1]

        # Aus Query-Parameter extrahieren
        if '?' in path:
            query = path.split('?')[1]
            for param in query.split('&'):
                if param.startswith('t='):
                    return param[2:]

        return None

    async def _handle_message(self, websocket: WebSocketServerProtocol, connection_id: str, call_id: str, message: str):
        """Behandelt eingehende Nachrichten mit erweiterter Validierung"""
        try:
            # Rate-Limit prüfen
            if not await self.connection_manager.check_rate_limit(connection_id):
                self.logger.warning(f"[{connection_id}] Rate-Limit überschritten für Call {call_id}")
                await websocket.close(code=1013, reason='rate limit exceeded')
                return

            # Aktivität aktualisieren
            self.connection_manager.update_activity(connection_id)

            # JSON parsen
            try:
                data = json.loads(message)
            except json.JSONDecodeError as e:
                self.logger.warning(f"[{connection_id}] Ungültiges JSON von Call {call_id}: {e}")
                await websocket.send(json.dumps({
                    "error": "Invalid JSON format",
                    "type": "error"
                }, ensure_ascii=False))
                return

            # Event validieren
            try:
                event = await self.validate_event(data)
            except ValueError as e:
                self.logger.warning(f"[{connection_id}] Event-Validierung fehlgeschlagen für Call {call_id}: {e}")
                await websocket.send(json.dumps({
                    "error": f"Event validation failed: {e}",
                    "type": "error"
                }, ensure_ascii=False))
                return

            # Event-Routing mit strukturiertem Logging
            if hasattr(event, 'type'):
                event_type = event.type
            else:
                event_type = getattr(event, '__root__', {}).get('type', 'unknown')
                
            if event_type == "audio_chunk":
                await self._handle_audio_chunk(event, call_id)
            elif event_type == "barge_in":
                await self._handle_barge_in(event, call_id)
            elif event_type == "ping":
                await self._handle_ping(event, call_id)
            elif event_type == "stop":
                await self._handle_stop(event, call_id)

        except Exception as e:
            self.logger.error(f"[{connection_id}] Nachrichtenfehler für Call {call_id}: {e}")
            await websocket.send(json.dumps({
                "error": "Internal server error",
                "type": "error"
            }, ensure_ascii=False))

    async def _handle_audio_chunk(self, event: WSEvent, call_id: str):
        """Behandelt Audio-Chunks - Mock-Flow für Realtime Loop Closure"""
        try:
            # Extrahiere Audio-Daten aus Event
            if hasattr(event, 'data'):
                audio_data = event.data
            else:
                audio_data = getattr(event, '__root__', {}).get('data', '')
            
            if not audio_data:
                self.logger.warning(f"[{call_id}] Leere Audio-Daten erhalten")
                return

            # Mock-Flow: Sofortige Antworten senden
            await self._send_mock_responses(call_id)
            
            self.logger.info(f"[{call_id}] Audio-Chunk verarbeitet: {len(audio_data)} chars")

        except Exception as e:
            self.logger.error(f"[{call_id}] Audio-Chunk Fehler: {e}")
            await self._send_error_response(call_id, "Audio processing failed")

    async def _handle_barge_in(self, event: WebSocketEvent, call_id: str):
        """Behandelt Barge-In Events"""
        try:
            barge_event = event.__root__

            # Barge-In an Redis Stream senden
            await self.redis_client.xadd(
                f"control_stream:{call_id}",
                {
                    "call_id": call_id,
                    "action": "barge_in",
                    "reason": barge_event.reason or "user_interrupted",
                    "timestamp": time.time()
                }
            )

            self.logger.info(f"[{call_id}] Barge-In registriert: {barge_event.reason}")

        except Exception as e:
            self.logger.error(f"[{call_id}] Barge-In-Fehler: {e}")

    async def _handle_ping(self, event: WSEvent, call_id: str):
        """Behandelt Ping Events"""
        # Pong-Antwort mit Mock-Response
        pong_response = create_mock_response('pong', ts=int(time.time() * 1000))

        # Pong an Client senden (falls Verbindung noch aktiv)
        if call_id in self.connection_manager.call_connections:
            connection_ids = self.connection_manager.call_connections[call_id]
            for conn_id in connection_ids:
                if conn_id in self.connection_manager.connections:
                    websocket = self.connection_manager.connections[conn_id]
                    try:
                        await websocket.send(json.dumps(pong_response, ensure_ascii=False))
                    except Exception as e:
                        self.logger.error(f"[{conn_id}] Pong-Fehler: {e}")

    async def _handle_stop(self, event: WebSocketEvent, call_id: str):
        """Behandelt Stop Events"""
        try:
            stop_event = event.__root__

            # Stop-Signal an Redis Stream senden
            await self.redis_client.xadd(
                f"control_stream:{call_id}",
                {
                    "call_id": call_id,
                    "action": "stop",
                    "reason": stop_event.reason or "client_request",
                    "timestamp": time.time()
                }
            )

            self.logger.info(f"[{call_id}] Stop-Signal gesendet")

        except Exception as e:
            self.logger.error(f"[{call_id}] Stop-Fehler: {e}")

    async def _send_mock_responses(self, call_id: str):
        """Sendet Mock-Responses für Realtime Loop Closure"""
        try:
            if call_id not in self.connection_manager.call_connections:
                return

            connection_ids = self.connection_manager.call_connections[call_id]
            timestamp = int(time.time() * 1000)

            # Mock-Responses in Sequenz senden
            responses = [
                create_mock_response('stt_final', text='Test erkannt', ts=timestamp + 100),
                create_mock_response('llm_token', text='Hallo,', ts=timestamp + 200),
                create_mock_response('llm_token', text=' ich', ts=timestamp + 250),
                create_mock_response('llm_token', text=' bin', ts=timestamp + 300),
                create_mock_response('llm_token', text=' TOM.', ts=timestamp + 350),
                create_mock_response('turn_end', ts=timestamp + 400),
                create_mock_response('tts_audio', ts=timestamp + 500)
            ]

            # Responses mit kleinen Delays senden
            for response in responses:
                await asyncio.sleep(0.05)  # 50ms Delay zwischen Responses
                
                for conn_id in connection_ids:
                    if conn_id in self.connection_manager.connections:
                        websocket = self.connection_manager.connections[conn_id]
                        try:
                            await websocket.send(json.dumps(response, ensure_ascii=False))
                        except Exception as e:
                            self.logger.error(f"[{conn_id}] Mock-Response Fehler: {e}")

            self.logger.info(f"[{call_id}] Mock-Responses gesendet")

        except Exception as e:
            self.logger.error(f"[{call_id}] Mock-Response Fehler: {e}")

    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Startet den WebSocket-Server"""
        try:
            await self.connect_redis()

            server = await asyncio.start_server(
                self.handle_websocket,
                host,
                port,
                reuse_address=True,
                reuse_port=True
            )

            self.logger.info(f"Telephony Bridge Server gestartet auf {host}:{port}")

            async with server:
                await server.serve_forever()

        except Exception as e:
            self.logger.error(f"Server-Start fehlgeschlagen: {e}")
            raise

async def main():
    """Hauptfunktion"""
    bridge = TelephonyBridge()

    try:
        await bridge.start_server()
    except KeyboardInterrupt:
        print("Server beendet durch Benutzer")
    except Exception as e:
        print(f"Server-Fehler: {e}")
    finally:
        if bridge.redis_client:
            await bridge.redis_client.close()

if __name__ == "__main__":
    asyncio.run(main())
