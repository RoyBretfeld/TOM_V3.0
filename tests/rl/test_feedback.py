"""
TOM v3.0 - RL Feedback Collector Tests
Unit-Tests für Feedback-Sammlung und -Validierung
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
import sqlite3

from apps.rl.feedback import FeedbackCollector, store_feedback, get_feedback_stats
from apps.rl.models import FeedbackEvent, FeedbackSignals, create_feedback_event


class TestFeedbackModels:
    """Tests für Feedback-Modelle"""
    
    def test_feedback_signals_valid(self):
        """Test für gültige Feedback-Signale"""
        signals = FeedbackSignals(
            resolution=True,
            user_rating=4,
            barge_in_count=1,
            handover=False,
            duration_sec=120.5,
            repeats=0
        )
        
        assert signals.resolution is True
        assert signals.user_rating == 4
        assert signals.barge_in_count == 1
        assert signals.handover is False
        assert signals.duration_sec == 120.5
        assert signals.repeats == 0
    
    def test_feedback_signals_minimal(self):
        """Test für minimale Feedback-Signale (nur resolution erforderlich)"""
        signals = FeedbackSignals(resolution=True)
        
        assert signals.resolution is True
        assert signals.user_rating is None
        assert signals.barge_in_count == 0
        assert signals.handover is False
    
    def test_feedback_signals_invalid_rating(self):
        """Test für ungültige Benutzerbewertung"""
        with pytest.raises(ValueError):
            FeedbackSignals(resolution=True, user_rating=6)
        
        with pytest.raises(ValueError):
            FeedbackSignals(resolution=True, user_rating=0)
    
    def test_feedback_event_valid(self):
        """Test für gültiges Feedback-Event"""
        event = FeedbackEvent(
            call_id="test_call_123",
            ts=datetime.now().timestamp(),
            agent="TOM",
            profile="kfz",
            policy_variant="v1a",
            signals=FeedbackSignals(resolution=True, user_rating=4)
        )
        
        assert event.call_id == "test_call_123"
        assert event.agent == "TOM"
        assert event.profile == "kfz"
        assert event.policy_variant == "v1a"
        assert event.signals.resolution is True
        assert event.signals.user_rating == 4
    
    def test_feedback_event_invalid_call_id(self):
        """Test für ungültige Call-ID"""
        with pytest.raises(ValueError):
            FeedbackEvent(
                call_id="",  # Leer
                ts=datetime.now().timestamp(),
                agent="TOM",
                profile="kfz",
                policy_variant="v1a",
                signals=FeedbackSignals(resolution=True)
            )
    
    def test_feedback_event_invalid_policy_variant(self):
        """Test für ungültige Policy-Variante"""
        with pytest.raises(ValueError):
            FeedbackEvent(
                call_id="test_call_123",
                ts=datetime.now().timestamp(),
                agent="TOM",
                profile="kfz",
                policy_variant="invalid",  # Ungültiges Format
                signals=FeedbackSignals(resolution=True)
            )
    
    def test_create_feedback_event_convenience(self):
        """Test für Convenience-Funktion"""
        event = create_feedback_event(
            call_id="test_call_123",
            agent="TOM",
            profile="kfz",
            policy_variant="v1a",
            resolution=True,
            user_rating=4
        )
        
        assert event.call_id == "test_call_123"
        assert event.agent == "TOM"
        assert event.profile == "kfz"
        assert event.policy_variant == "v1a"
        assert event.signals.resolution is True
        assert event.signals.user_rating == 4


class TestFeedbackCollector:
    """Tests für Feedback Collector"""
    
    @pytest.fixture
    def temp_db(self):
        """Temporäre Datenbank für Tests"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    def test_feedback_collector_init(self, temp_db):
        """Test für Feedback Collector Initialisierung"""
        collector = FeedbackCollector(temp_db)
        
        assert collector.db_path == Path(temp_db)
        assert collector.db_path.exists()
    
    def test_store_feedback_valid(self, temp_db):
        """Test für gültiges Feedback-Event speichern"""
        collector = FeedbackCollector(temp_db)
        
        event = {
            "call_id": "test_call_123",
            "ts": datetime.now().timestamp(),
            "agent": "TOM",
            "profile": "kfz",
            "policy_variant": "v1a",
            "signals": {
                "resolution": True,
                "user_rating": 4,
                "barge_in_count": 1,
                "handover": False,
                "duration_sec": 120.5,
                "repeats": 0
            }
        }
        
        result = collector.store_feedback(event)
        assert result is True
        
        # Prüfe ob Event in Datenbank gespeichert wurde
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM feedback")
            count = cursor.fetchone()[0]
            assert count == 1
    
    def test_store_feedback_invalid(self, temp_db):
        """Test für ungültiges Feedback-Event"""
        collector = FeedbackCollector(temp_db)
        
        # Ungültiges Event (fehlende erforderliche Felder)
        invalid_event = {
            "call_id": "test_call_123",
            "ts": datetime.now().timestamp(),
            "agent": "TOM",
            "profile": "kfz",
            "policy_variant": "v1a",
            "signals": {
                # resolution fehlt (erforderlich)
                "user_rating": 4
            }
        }
        
        result = collector.store_feedback(invalid_event)
        assert result is False
    
    def test_get_feedback_by_policy(self, temp_db):
        """Test für Abrufen von Feedback-Events nach Policy"""
        collector = FeedbackCollector(temp_db)
        
        # Mehrere Events speichern
        events = [
            {
                "call_id": "test_call_1",
                "ts": datetime.now().timestamp(),
                "agent": "TOM",
                "profile": "kfz",
                "policy_variant": "v1a",
                "signals": {"resolution": True, "user_rating": 4}
            },
            {
                "call_id": "test_call_2",
                "ts": datetime.now().timestamp(),
                "agent": "TOM",
                "profile": "it",
                "policy_variant": "v1a",
                "signals": {"resolution": False, "user_rating": 2}
            },
            {
                "call_id": "test_call_3",
                "ts": datetime.now().timestamp(),
                "agent": "TOM",
                "profile": "sales",
                "policy_variant": "v1b",
                "signals": {"resolution": True, "user_rating": 5}
            }
        ]
        
        for event in events:
            collector.store_feedback(event)
        
        # Events für v1a abrufen
        v1a_events = collector.get_feedback_by_policy("v1a")
        assert len(v1a_events) == 2
        
        # Events für v1b abrufen
        v1b_events = collector.get_feedback_by_policy("v1b")
        assert len(v1b_events) == 1
    
    def test_get_feedback_stats(self, temp_db):
        """Test für Feedback-Statistiken"""
        collector = FeedbackCollector(temp_db)
        
        # Mehrere Events speichern
        events = [
            {
                "call_id": "test_call_1",
                "ts": datetime.now().timestamp(),
                "agent": "TOM",
                "profile": "kfz",
                "policy_variant": "v1a",
                "signals": {"resolution": True}
            },
            {
                "call_id": "test_call_2",
                "ts": datetime.now().timestamp(),
                "agent": "TOM",
                "profile": "it",
                "policy_variant": "v1a",
                "signals": {"resolution": True}
            },
            {
                "call_id": "test_call_3",
                "ts": datetime.now().timestamp(),
                "agent": "TOM",
                "profile": "sales",
                "policy_variant": "v1b",
                "signals": {"resolution": True}
            }
        ]
        
        for event in events:
            collector.store_feedback(event)
        
        stats = collector.get_feedback_stats()
        
        assert stats['total_events'] == 3
        assert stats['policy_stats']['v1a'] == 2
        assert stats['policy_stats']['v1b'] == 1
        assert stats['profile_stats']['kfz'] == 1
        assert stats['profile_stats']['it'] == 1
        assert stats['profile_stats']['sales'] == 1
    
    def test_cleanup_old_events(self, temp_db):
        """Test für Löschen alter Events"""
        collector = FeedbackCollector(temp_db)
        
        # Altes Event speichern (vor 100 Tagen)
        old_ts = datetime.now().timestamp() - (100 * 24 * 3600)
        old_event = {
            "call_id": "old_call",
            "ts": old_ts,
            "agent": "TOM",
            "profile": "kfz",
            "policy_variant": "v1a",
            "signals": {"resolution": True}
        }
        
        collector.store_feedback(old_event)
        
        # Neues Event speichern
        new_event = {
            "call_id": "new_call",
            "ts": datetime.now().timestamp(),
            "agent": "TOM",
            "profile": "kfz",
            "policy_variant": "v1a",
            "signals": {"resolution": True}
        }
        
        collector.store_feedback(new_event)
        
        # Cleanup (Events älter als 90 Tage)
        deleted_count = collector.cleanup_old_events(days=90)
        assert deleted_count == 1
        
        # Prüfe ob nur neues Event übrig ist
        stats = collector.get_feedback_stats()
        assert stats['total_events'] == 1


class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    @pytest.fixture
    def temp_db(self):
        """Temporäre Datenbank für Tests"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    def test_store_feedback_convenience(self, temp_db, monkeypatch):
        """Test für store_feedback Convenience-Funktion"""
        # Mock der globalen Instanz
        collector = FeedbackCollector(temp_db)
        monkeypatch.setattr('apps.rl.feedback.feedback_collector', collector)
        
        event = {
            "call_id": "test_call_123",
            "ts": datetime.now().timestamp(),
            "agent": "TOM",
            "profile": "kfz",
            "policy_variant": "v1a",
            "signals": {"resolution": True, "user_rating": 4}
        }
        
        result = store_feedback(event)
        assert result is True
    
    def test_get_feedback_stats_convenience(self, temp_db, monkeypatch):
        """Test für get_feedback_stats Convenience-Funktion"""
        # Mock der globalen Instanz
        collector = FeedbackCollector(temp_db)
        monkeypatch.setattr('apps.rl.feedback.feedback_collector', collector)
        
        stats = get_feedback_stats()
        assert 'total_events' in stats
        assert 'policy_stats' in stats
        assert 'profile_stats' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
