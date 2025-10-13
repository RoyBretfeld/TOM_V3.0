"""
Tests für End-of-Call Feedback Collection
"""

import pytest
from unittest.mock import patch, AsyncMock, Mock
from apps.dispatcher.closing import FeedbackCollector, ask_feedback, parse_rating

class TestFeedbackCollector:
    """Tests für FeedbackCollector"""
    
    def test_init(self):
        """Test Initialisierung"""
        collector = FeedbackCollector()
        assert collector.feedback_patterns['rating'] is not None
        assert collector.feedback_patterns['direct_number'] is not None
        assert 'words' in collector.feedback_patterns
        
    def test_get_feedback_prompt(self):
        """Test Feedback-Prompt-Generierung"""
        collector = FeedbackCollector()
        
        prompt_v1a = collector._get_feedback_prompt('v1a')
        assert "bewerten" in prompt_v1a.lower()
        assert "1 bis 5" in prompt_v1a
        
        prompt_v5a = collector._get_feedback_prompt('v5a')
        assert "😊" in prompt_v5a
        
        # Unbekannte Variante
        prompt_unknown = collector._get_feedback_prompt('unknown')
        assert prompt_unknown == collector._get_feedback_prompt('v1a')
        
    def test_parse_rating_direct_numbers(self):
        """Test Parsing direkter Zahlen"""
        collector = FeedbackCollector()
        
        assert collector._parse_rating("5") == 5
        assert collector._parse_rating("Bewertung 4") == 4
        assert collector._parse_rating("Das war eine 3") == 3
        assert collector._parse_rating("Note: 2") == 2
        assert collector._parse_rating("1 Sterne") == 1
        
    def test_parse_rating_words(self):
        """Test Parsing von Wörtern"""
        collector = FeedbackCollector()
        
        assert collector._parse_rating("sehr gut") == 5
        assert collector._parse_rating("exzellent") == 5
        assert collector._parse_rating("gut") == 4
        assert collector._parse_rating("okay") == 3
        assert collector._parse_rating("schlecht") == 2
        assert collector._parse_rating("gar nicht") == 1
        
    def test_parse_rating_edge_cases(self):
        """Test Edge Cases"""
        collector = FeedbackCollector()
        
        assert collector._parse_rating("") is None
        assert collector._parse_rating(None) is None
        assert collector._parse_rating("keine bewertung") is None
        assert collector._parse_rating("6") is None  # Zu hoch
        assert collector._parse_rating("0") is None  # Zu niedrig
        
    @pytest.mark.asyncio
    async def test_simulate_user_response(self):
        """Test Benutzerantwort-Simulation"""
        collector = FeedbackCollector()
        
        response = await collector._simulate_user_response()
        assert isinstance(response, str)
        assert len(response) > 0
        
        # Mehrere Aufrufe sollten verschiedene Antworten geben
        responses = set()
        for _ in range(10):
            response = await collector._simulate_user_response()
            responses.add(response)
        
        # Sollte verschiedene Antworten geben (mit hoher Wahrscheinlichkeit)
        assert len(responses) > 1
        
    @pytest.mark.asyncio
    async def test_ask_feedback_success(self):
        """Test erfolgreiche Feedback-Sammlung"""
        collector = FeedbackCollector()
        
        session_context = {
            'policy_variant': 'v1a',
            'profile': 'kfz',
            'duration_sec': 120,
            'barge_in_count': 1,
            'repeats': 0
        }
        
        with patch('apps.dispatcher.closing.store_feedback') as mock_store:
            with patch.object(collector, '_simulate_user_response', return_value="Das war sehr gut, 5!"):
                rating = await collector.ask_feedback("test_call_123", session_context)
                
                assert rating == 5
                mock_store.assert_called_once()
                
                # Prüfe gespeichertes Event
                call_args = mock_store.call_args[0][0]
                assert call_args.call_id == "test_call_123"
                assert call_args.policy_variant == "v1a"
                assert call_args.profile == "kfz"
                assert call_args.signals.user_rating == 5
                
    @pytest.mark.asyncio
    async def test_ask_feedback_parse_error(self):
        """Test bei Parsing-Fehler"""
        collector = FeedbackCollector()
        
        session_context = {'policy_variant': 'v1a', 'profile': 'general'}
        
        with patch.object(collector, '_simulate_user_response', return_value="unverständliche antwort"):
            rating = await collector.ask_feedback("test_call_456", session_context)
            
            assert rating is None
            
    @pytest.mark.asyncio
    async def test_ask_feedback_exception(self):
        """Test bei Exception"""
        collector = FeedbackCollector()
        
        with patch('apps.dispatcher.closing.store_feedback', side_effect=Exception("DB Error")):
            rating = await collector.ask_feedback("test_call_789", {})
            
            assert rating is None

class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    @pytest.mark.asyncio
    async def test_ask_feedback_convenience(self):
        """Test ask_feedback Convenience-Funktion"""
        with patch('apps.dispatcher.closing._get_feedback_collector') as mock_get_collector:
            mock_collector = AsyncMock()
            mock_collector.ask_feedback.return_value = 4
            mock_get_collector.return_value = mock_collector
            
            result = await ask_feedback("test_call", {'policy_variant': 'v1a'})
            
            assert result == 4
            mock_collector.ask_feedback.assert_called_once_with("test_call", {'policy_variant': 'v1a'})
            
    def test_parse_rating_convenience(self):
        """Test parse_rating Convenience-Funktion"""
        with patch('apps.dispatcher.closing._get_feedback_collector') as mock_get_collector:
            mock_collector = Mock()
            mock_collector._parse_rating.return_value = 3
            mock_get_collector.return_value = mock_collector
            
            result = parse_rating("okay")
            
            assert result == 3
            mock_collector._parse_rating.assert_called_once_with("okay")

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
