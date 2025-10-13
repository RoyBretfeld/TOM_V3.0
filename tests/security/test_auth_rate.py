#!/usr/bin/env python3
"""
TOM v3.0 - Security Tests für Authentifizierung und Rate-Limiting

Tests für:
- JWT-Authentifizierung
- Replay-Schutz
- Rate-Limiting
- Call-ID-Validierung

CSB v1 Compliance:
- UTF-8 Encoding für alle Testausgaben
- Strukturierte Fehlerbehandlung
- Keine Debug-Logs über WARN hinaus
"""
import asyncio
import json
import time
import jwt
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# UTF-8 Encoding sicherstellen
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Projekt-Root zu Python-Path hinzufügen
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from apps.telephony_bridge.ws import (
    TelephonyBridge,
    Config,
    AudioChunk,
    BargeIn,
    Ping,
    Stop
)

class TestJWTAuthentication:
    """Tests für JWT-Authentifizierung"""

    @pytest.fixture
    def bridge(self):
        """Erstellt Test-Bridge-Instanz"""
        return TelephonyBridge()

    def create_test_token(self, call_id: str, nonce: str = None, exp_offset: int = 3600):
        """Erstellt ein gültiges Test-Token"""
        payload = {
            'sub': 'test-user',
            'call_id': call_id,
            'iat': int(time.time()),
            'exp': int(time.time()) + exp_offset
        }
        if nonce:
            payload['nonce'] = nonce

        return jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')

    @pytest.mark.asyncio
    async def test_valid_jwt_authentication(self, bridge):
        """Test: Gültiges JWT wird akzeptiert"""
        call_id = "test-call-123"
        token = self.create_test_token(call_id)

        with patch.object(bridge, 'redis_client') as mock_redis:
            mock_redis.exists = AsyncMock(return_value=False)

            # Sollte ohne Fehler validiert werden
            payload = await bridge.authenticate_jwt(token, call_id)

            assert payload['call_id'] == call_id
            assert payload['sub'] == 'test-user'

    @pytest.mark.asyncio
    async def test_call_id_mismatch(self, bridge):
        """Test: Falsche Call-ID wird abgelehnt"""
        token_call_id = "wrong-call"
        expected_call_id = "test-call-123"
        token = self.create_test_token(token_call_id)

        with patch.object(bridge, 'redis_client') as mock_redis:
            with pytest.raises(jwt.InvalidTokenError, match="Call ID mismatch"):
                await bridge.authenticate_jwt(token, expected_call_id)

    @pytest.mark.asyncio
    async def test_replay_attack_detection(self, bridge):
        """Test: Replay-Attack wird erkannt"""
        call_id = "test-call-123"
        nonce = "test-nonce-123"
        token = self.create_test_token(call_id, nonce)

        with patch.object(bridge, 'redis_client') as mock_redis:
            # Nonce bereits verwendet
            mock_redis.exists = AsyncMock(return_value=True)

            with pytest.raises(jwt.InvalidTokenError, match="Nonce bereits verwendet"):
                await bridge.authenticate_jwt(token, call_id)

    @pytest.mark.asyncio
    async def test_expired_token(self, bridge):
        """Test: Abgelaufenes Token wird abgelehnt"""
        call_id = "test-call-123"
        token = self.create_test_token(call_id, exp_offset=-3600)  # Vor einer Stunde abgelaufen

        with patch.object(bridge, 'redis_client') as mock_redis:
            with pytest.raises(jwt.InvalidTokenError, match="Token abgelaufen"):
                await bridge.authenticate_jwt(token, call_id)

    @pytest.mark.asyncio
    async def test_malformed_token(self, bridge):
        """Test: Unvollständiges Token wird abgelehnt"""
        call_id = "test-call-123"
        malformed_token = "not.a.valid.token"

        with patch.object(bridge, 'redis_client') as mock_redis:
            with pytest.raises(jwt.InvalidTokenError):
                await bridge.authenticate_jwt(malformed_token, call_id)

class TestRateLimiting:
    """Tests für Rate-Limiting"""

    @pytest.fixture
    def bridge(self):
        """Erstellt Test-Bridge-Instanz"""
        return TelephonyBridge()

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, bridge):
        """Test: Rate-Limit wird durchgesetzt"""
        connection_id = "test-connection"

        # Verbindung hinzufügen
        mock_ws = AsyncMock()
        await bridge.connection_manager.add_connection(connection_id, mock_ws, "test-call")

        # Erste 120 Nachrichten sollten funktionieren
        for i in range(120):
            assert await bridge.connection_manager.check_rate_limit(connection_id) == True

        # 121. Nachricht sollte blockiert werden
        assert await bridge.connection_manager.check_rate_limit(connection_id) == False

    @pytest.mark.asyncio
    async def test_rate_limit_per_connection(self, bridge):
        """Test: Rate-Limit ist pro Verbindung"""
        conn1 = "connection-1"
        conn2 = "connection-2"

        # Beide Verbindungen hinzufügen
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        await bridge.connection_manager.add_connection(conn1, mock_ws1, "call-1")
        await bridge.connection_manager.add_connection(conn2, mock_ws2, "call-2")

        # Beide können 120 Nachrichten senden
        for conn_id in [conn1, conn2]:
            for i in range(120):
                assert await bridge.connection_manager.check_rate_limit(conn_id) == True

        # Beide sollten jetzt limitiert sein
        for conn_id in [conn1, conn2]:
            assert await bridge.connection_manager.check_rate_limit(conn_id) == False

class TestEventValidation:
    """Tests für Event-Validierung"""

    @pytest.fixture
    def bridge(self):
        """Erstellt Test-Bridge-Instanz"""
        return TelephonyBridge()

    def test_valid_audio_chunk(self, bridge):
        """Test: Gültiger Audio-Chunk wird akzeptiert"""
        event_data = {
            "type": "audio_chunk",
            "ts": time.time(),
            "format": "pcm16_16k",
            "bytes": "dGVzdCBkYXRh"  # "test data" in base64
        }

        # Sollte ohne Fehler validiert werden
        validated = asyncio.run(bridge.validate_event(event_data))
        assert validated.type == "audio_chunk"

    def test_invalid_audio_format(self, bridge):
        """Test: Falsches Audio-Format wird abgelehnt"""
        event_data = {
            "type": "audio_chunk",
            "ts": time.time(),
            "format": "mp3",  # Ungültiges Format
            "bytes": "dGVzdCBkYXRh"
        }

        with pytest.raises(ValueError, match="Unsupported audio format"):
            asyncio.run(bridge.validate_event(event_data))

    def test_missing_required_fields(self, bridge):
        """Test: Fehlende Felder werden abgelehnt"""
        invalid_events = [
            {"type": "audio_chunk"},  # Fehlende Felder
            {"type": "barge_in", "reason": None},  # Keine Call-ID
            {"type": "ping"},  # Keine Call-ID
            {"type": "unknown_type"}  # Unbekannter Typ
        ]

        for event_data in invalid_events:
            with pytest.raises(ValueError):
                asyncio.run(bridge.validate_event(event_data))

class TestConnectionManagement:
    """Tests für Connection-Management"""

    @pytest.fixture
    def bridge(self):
        """Erstellt Test-Bridge-Instanz"""
        return TelephonyBridge()

    @pytest.mark.asyncio
    async def test_connection_lifecycle(self, bridge):
        """Test: Verbindung wird korrekt verwaltet"""
        connection_id = "test-connection"
        call_id = "test-call"

        # Mock WebSocket
        mock_ws = AsyncMock()

        # Verbindung hinzufügen
        await bridge.connection_manager.add_connection(connection_id, mock_ws, call_id)

        assert connection_id in bridge.connection_manager.connections
        assert call_id in bridge.connection_manager.call_connections
        assert connection_id in bridge.connection_manager.rate_limiters

        # Verbindung entfernen
        await bridge.connection_manager.remove_connection(connection_id, call_id)

        assert connection_id not in bridge.connection_manager.connections
        assert call_id not in bridge.connection_manager.call_connections

if __name__ == '__main__':
    # Direkte Testausführung ohne komplexe Dependencies
    print("🧪 Führe Security-Tests aus...")

    # Einfache Tests ohne Pytest
    test_suite = TestJWTAuthentication()
    bridge = TelephonyBridge()

    # Test 1: Gültiges Token
    print("Testing valid JWT authentication...")
    token = test_suite.create_test_token("test-call")

    # Mock Redis für diesen Test
    with patch.object(bridge, 'redis_client') as mock_redis:
        mock_redis.exists = AsyncMock(return_value=False)
        try:
            payload = asyncio.run(bridge.authenticate_jwt(token, "test-call"))
            print("✅ Valid JWT authentication passed")
        except Exception as e:
            print(f"❌ Valid JWT authentication failed: {e}")

    # Test 2: Call-ID Mismatch
    print("Testing call ID mismatch...")
    with patch.object(bridge, 'redis_client') as mock_redis:
        try:
            asyncio.run(bridge.authenticate_jwt(token, "wrong-call"))
            print("❌ Call ID mismatch test failed")
        except jwt.InvalidTokenError:
            print("✅ Call ID mismatch test passed")

    # Test 3: Event Validierung
    print("Testing event validation...")
    try:
        valid_event = {
            "type": "audio_chunk",
            "ts": time.time(),
            "format": "pcm16_16k",
            "bytes": "dGVzdCBkYXRh"
        }
        validated = asyncio.run(bridge.validate_event(valid_event))
        print("✅ Valid event validation passed")
    except Exception as e:
        print(f"❌ Valid event validation failed: {e}")

    print("🎯 Security-Tests abgeschlossen!")
