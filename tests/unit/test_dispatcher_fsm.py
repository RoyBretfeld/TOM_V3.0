"""
TOM v3.0 - Dispatcher FSM Tests (Vereinfacht)
Unit-Tests für FSM mit RL Policy Router Integration
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch, MagicMock

from apps.dispatcher.rt_fsm import (
    RealtimeFSM, CallState, CallEvent, CallContext, CallSession,
    create_call_session, handle_call_event, get_call_policy, update_call_context
)


class TestCallState:
    """Tests für Call-Zustände"""
    
    def test_call_state_values(self):
        """Test für Call-State-Werte"""
        assert CallState.IDLE.value == "idle"
        assert CallState.RINGING.value == "ringing"
        assert CallState.CONNECTED.value == "connected"
        assert CallState.LISTENING.value == "listening"
        assert CallState.THINKING.value == "thinking"
        assert CallState.SPEAKING.value == "speaking"
        assert CallState.BARRED.value == "barred"
        assert CallState.ENDED.value == "ended"


class TestCallEvent:
    """Tests für Call-Events"""
    
    def test_call_event_values(self):
        """Test für Call-Event-Werte"""
        assert CallEvent.INCOMING_CALL.value == "incoming_call"
        assert CallEvent.CALL_ANSWERED.value == "call_answered"
        assert CallEvent.CALL_ENDED.value == "call_ended"
        assert CallEvent.AUDIO_START.value == "audio_start"
        assert CallEvent.AUDIO_STOP.value == "audio_stop"
        assert CallEvent.BARGE_IN.value == "barge_in"
        assert CallEvent.TIMEOUT.value == "timeout"
        assert CallEvent.ERROR.value == "error"


class TestCallContext:
    """Tests für Call-Kontext"""
    
    def test_call_context_creation(self):
        """Test für Call-Kontext Erstellung"""
        context = CallContext(
            call_id="test_call_123",
            profile="kfz",
            time_of_day="morning"
        )
        
        assert context.call_id == "test_call_123"
        assert context.profile == "kfz"
        assert context.time_of_day == "morning"
        assert context.call_duration == 0.0
        assert context.barge_in_count == 0
        assert context.repeat_count == 0
        assert context.user_rating is None
        assert context.resolution is False
        assert context.handover is False


class TestCallSession:
    """Tests für Call-Session"""
    
    def test_call_session_creation(self):
        """Test für Call-Session Erstellung"""
        context = CallContext("test_call_123")
        session = CallSession(
            call_id="test_call_123",
            context=context,
            policy_variant="v1a"
        )
        
        assert session.call_id == "test_call_123"
        assert session.state == CallState.IDLE
        assert session.policy_variant == "v1a"
        assert session.context == context
        assert len(session.events) == 0
    
    def test_call_session_to_dict(self):
        """Test für Call-Session Serialisierung"""
        context = CallContext("test_call_123", profile="kfz")
        session = CallSession(
            call_id="test_call_123",
            context=context,
            policy_variant="v1a"
        )
        
        session_dict = session.to_dict()
        
        assert session_dict["call_id"] == "test_call_123"
        assert session_dict["state"] == "idle"
        assert session_dict["policy_variant"] == "v1a"
        assert session_dict["context"]["profile"] == "kfz"
        assert "start_time" in session_dict
        assert "last_activity" in session_dict
        assert "events" in session_dict


class TestRealtimeFSM:
    """Tests für Realtime FSM"""
    
    @pytest.fixture
    def fsm(self):
        """FSM-Instanz für Tests"""
        return RealtimeFSM()
    
    @pytest.mark.asyncio
    async def test_fsm_initialization(self, fsm):
        """Test für FSM-Initialisierung"""
        assert len(fsm.sessions) == 0
        assert CallState.IDLE in fsm.transitions
        assert CallState.ENDED in fsm.transitions
    
    @pytest.mark.asyncio
    async def test_create_session(self, fsm):
        """Test für Session-Erstellung"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            session = await fsm.create_session("test_call_123", "kfz")
            
            assert session.call_id == "test_call_123"
            assert session.context.profile == "kfz"
            assert session.policy_variant == "v1a"
            assert session.state == CallState.IDLE
            assert "test_call_123" in fsm.sessions
            
            mock_bandit.select.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_event_valid_transition(self, fsm):
        """Test für gültige Event-Transition"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            # Session erstellen
            await fsm.create_session("test_call_123")
            
            # Event behandeln
            result = await fsm.handle_event("test_call_123", CallEvent.INCOMING_CALL)
            
            assert result is True
            session = fsm.sessions["test_call_123"]
            assert session.state == CallState.RINGING
            assert len(session.events) == 1
            assert session.events[0]["event"] == "incoming_call"
    
    @pytest.mark.asyncio
    async def test_handle_event_invalid_transition(self, fsm):
        """Test für ungültige Event-Transition"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            # Session erstellen
            await fsm.create_session("test_call_123")
            
            # Ungültige Transition versuchen
            result = await fsm.handle_event("test_call_123", CallEvent.AUDIO_START)
            
            assert result is False
            session = fsm.sessions["test_call_123"]
            assert session.state == CallState.IDLE  # Sollte unverändert bleiben
    
    @pytest.mark.asyncio
    async def test_handle_event_unknown_session(self, fsm):
        """Test für Event mit unbekannter Session"""
        result = await fsm.handle_event("unknown_call", CallEvent.INCOMING_CALL)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_session(self, fsm):
        """Test für Session-Abruf"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            await fsm.create_session("test_call_123")
            
            session = await fsm.get_session("test_call_123")
            assert session is not None
            assert session.call_id == "test_call_123"
            
            unknown_session = await fsm.get_session("unknown_call")
            assert unknown_session is None
    
    @pytest.mark.asyncio
    async def test_get_policy_for_session(self, fsm):
        """Test für Policy-Abruf"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v2a"
            
            await fsm.create_session("test_call_123")
            
            policy = await fsm.get_policy_for_session("test_call_123")
            assert policy == "v2a"
            
            unknown_policy = await fsm.get_policy_for_session("unknown_call")
            assert unknown_policy is None
    
    @pytest.mark.asyncio
    async def test_update_session_context(self, fsm):
        """Test für Kontext-Aktualisierung"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            session = await fsm.create_session("test_call_123")
            
            # Kontext aktualisieren
            result = await fsm.update_session_context(
                "test_call_123",
                user_rating=5,
                resolution=True,
                barge_in_count=2
            )
            
            assert result is True
            assert session.context.user_rating == 5
            assert session.context.resolution is True
            assert session.context.barge_in_count == 2
            
            # Unbekannte Session
            result = await fsm.update_session_context("unknown_call", user_rating=3)
            assert result is False
    
    @pytest.mark.asyncio
    async def test_get_session_stats(self, fsm):
        """Test für Session-Statistiken"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            # Mehrere Sessions erstellen
            await fsm.create_session("call_1")
            await fsm.create_session("call_2")
            
            # Events hinzufügen
            await fsm.handle_event("call_1", CallEvent.INCOMING_CALL)
            await fsm.handle_event("call_2", CallEvent.INCOMING_CALL)
            await fsm.handle_event("call_2", CallEvent.CALL_ANSWERED)
            
            stats = fsm.get_session_stats()
            
            assert stats["active_sessions"] == 2
            assert stats["state_distribution"]["ringing"] == 1  # call_2 ist nach CALL_ANSWERED in CONNECTED
            assert stats["state_distribution"]["connected"] == 1  # call_2 ist nach CALL_ANSWERED in CONNECTED
            assert stats["total_events"] == 3
    
    def test_time_of_day_detection(self, fsm):
        """Test für Tageszeit-Erkennung"""
        # Einfacher Test ohne Mock
        time_of_day = fsm._get_time_of_day()
        assert time_of_day in ["morning", "afternoon", "evening", "night"]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])