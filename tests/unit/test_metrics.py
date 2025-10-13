"""
Tests für RL Metrics Exporter
"""

import pytest
from unittest.mock import patch, Mock
from apps.monitor.metrics import (
    RLMetricsExporter, 
    record_feedback, record_reward, record_user_rating,
    record_policy_pull, update_success_rate, update_exploration_rate,
    update_active_variants, update_blacklisted_variants,
    record_session_duration, record_barge_in, record_escalation,
    get_metrics, get_metrics_dict, rl_registry
)

class TestRLMetricsExporter:
    """Tests für RLMetricsExporter"""
    
    def test_init(self):
        """Test Initialisierung"""
        exporter = RLMetricsExporter()
        assert exporter.last_update is not None
        
    def test_record_feedback(self):
        """Test Feedback-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_feedback_total') as mock_counter:
            exporter.record_feedback("v1a", "kfz", "TOM")
            mock_counter.labels.assert_called_once_with(
                policy_variant="v1a",
                profile="kfz", 
                agent="TOM"
            )
            mock_counter.labels.return_value.inc.assert_called_once()
            
    def test_record_reward(self):
        """Test Reward-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_reward_histogram') as mock_histogram:
            exporter.record_reward("v1a", 0.7)
            mock_histogram.labels.assert_called_once_with(policy_variant="v1a")
            mock_histogram.labels.return_value.observe.assert_called_once_with(0.7)
            
    def test_record_user_rating(self):
        """Test Benutzerbewertung-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_user_rating_histogram') as mock_histogram:
            exporter.record_user_rating("v1a", 4)
            mock_histogram.labels.assert_called_once_with(policy_variant="v1a")
            mock_histogram.labels.return_value.observe.assert_called_once_with(4)
            
    def test_record_user_rating_invalid(self):
        """Test ungültige Benutzerbewertung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_user_rating_histogram') as mock_histogram:
            exporter.record_user_rating("v1a", 6)  # Ungültig
            mock_histogram.labels.assert_not_called()
            
    def test_record_policy_pull(self):
        """Test Policy-Pull-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_policy_pulls_total') as mock_counter:
            exporter.record_policy_pull("v1a")
            mock_counter.labels.assert_called_once_with(policy_variant="v1a")
            mock_counter.labels.return_value.inc.assert_called_once()
            
    def test_update_success_rate(self):
        """Test Erfolgsrate-Update"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_policy_success_rate') as mock_gauge:
            exporter.update_success_rate("v1a", 0.85)
            mock_gauge.labels.assert_called_once_with(policy_variant="v1a")
            mock_gauge.labels.return_value.set.assert_called_once_with(0.85)
            
    def test_update_exploration_rate(self):
        """Test Exploration-Rate-Update"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_bandit_exploration_rate') as mock_gauge:
            exporter.update_exploration_rate(0.15)
            mock_gauge.set.assert_called_once_with(0.15)
            
    def test_update_active_variants(self):
        """Test aktive Varianten-Update"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_active_variants') as mock_gauge:
            exporter.update_active_variants(5)
            mock_gauge.set.assert_called_once_with(5)
            
    def test_update_blacklisted_variants(self):
        """Test schwarze Varianten-Update"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_blacklisted_variants') as mock_gauge:
            exporter.update_blacklisted_variants(2)
            mock_gauge.set.assert_called_once_with(2)
            
    def test_record_session_duration(self):
        """Test Session-Dauer-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_session_duration_histogram') as mock_histogram:
            exporter.record_session_duration("v1a", 180.5)
            mock_histogram.labels.assert_called_once_with(policy_variant="v1a")
            mock_histogram.labels.return_value.observe.assert_called_once_with(180.5)
            
    def test_record_barge_in(self):
        """Test Barge-In-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_barge_in_total') as mock_counter:
            exporter.record_barge_in("v1a", 3)
            mock_counter.labels.assert_called_once_with(policy_variant="v1a")
            mock_counter.labels.return_value.inc.assert_called_once_with(3)
            
    def test_record_escalation(self):
        """Test Eskalation-Aufzeichnung"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.rl_escalation_total') as mock_counter:
            exporter.record_escalation("v1a")
            mock_counter.labels.assert_called_once_with(policy_variant="v1a")
            mock_counter.labels.return_value.inc.assert_called_once()
            
    def test_get_metrics(self):
        """Test Metriken-Ausgabe"""
        exporter = RLMetricsExporter()
        
        with patch('apps.monitor.metrics.generate_latest') as mock_generate:
            mock_generate.return_value = b"# HELP test_metric Test metric\n# TYPE test_metric counter\ntest_metric 42\n"
            
            metrics = exporter.get_metrics()
            assert metrics == "# HELP test_metric Test metric\n# TYPE test_metric counter\ntest_metric 42\n"
            mock_generate.assert_called_once_with(rl_registry)
            
    def test_get_metrics_dict(self):
        """Test Metriken-Dictionary"""
        exporter = RLMetricsExporter()
        
        with patch.object(exporter, 'get_metrics', return_value="test_metric 42\nother_metric 3.14\n"):
            metrics_dict = exporter.get_metrics_dict()
            
            assert metrics_dict == {
                "test_metric": 42.0,
                "other_metric": 3.14
            }

class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    def test_record_feedback_convenience(self):
        """Test record_feedback Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_feedback("v1a", "kfz", "TOM")
            
            mock_exporter.record_feedback.assert_called_once_with("v1a", "kfz", "TOM")
            
    def test_record_reward_convenience(self):
        """Test record_reward Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_reward("v1a", 0.7)
            
            mock_exporter.record_reward.assert_called_once_with("v1a", 0.7)
            
    def test_record_user_rating_convenience(self):
        """Test record_user_rating Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_user_rating("v1a", 4)
            
            mock_exporter.record_user_rating.assert_called_once_with("v1a", 4)
            
    def test_record_policy_pull_convenience(self):
        """Test record_policy_pull Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_policy_pull("v1a")
            
            mock_exporter.record_policy_pull.assert_called_once_with("v1a")
            
    def test_update_success_rate_convenience(self):
        """Test update_success_rate Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            update_success_rate("v1a", 0.85)
            
            mock_exporter.update_success_rate.assert_called_once_with("v1a", 0.85)
            
    def test_update_exploration_rate_convenience(self):
        """Test update_exploration_rate Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            update_exploration_rate(0.15)
            
            mock_exporter.update_exploration_rate.assert_called_once_with(0.15)
            
    def test_update_active_variants_convenience(self):
        """Test update_active_variants Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            update_active_variants(5)
            
            mock_exporter.update_active_variants.assert_called_once_with(5)
            
    def test_update_blacklisted_variants_convenience(self):
        """Test update_blacklisted_variants Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            update_blacklisted_variants(2)
            
            mock_exporter.update_blacklisted_variants.assert_called_once_with(2)
            
    def test_record_session_duration_convenience(self):
        """Test record_session_duration Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_session_duration("v1a", 180.5)
            
            mock_exporter.record_session_duration.assert_called_once_with("v1a", 180.5)
            
    def test_record_barge_in_convenience(self):
        """Test record_barge_in Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_barge_in("v1a", 3)
            
            mock_exporter.record_barge_in.assert_called_once_with("v1a", 3)
            
    def test_record_escalation_convenience(self):
        """Test record_escalation Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_get_exporter.return_value = mock_exporter
            
            record_escalation("v1a")
            
            mock_exporter.record_escalation.assert_called_once_with("v1a")
            
    def test_get_metrics_convenience(self):
        """Test get_metrics Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.get_metrics.return_value = "test metrics"
            mock_get_exporter.return_value = mock_exporter
            
            result = get_metrics()
            
            assert result == "test metrics"
            mock_exporter.get_metrics.assert_called_once()
            
    def test_get_metrics_dict_convenience(self):
        """Test get_metrics_dict Convenience-Funktion"""
        with patch('apps.monitor.metrics._get_metrics_exporter') as mock_get_exporter:
            mock_exporter = Mock()
            mock_exporter.get_metrics_dict.return_value = {"test": 42}
            mock_get_exporter.return_value = mock_exporter
            
            result = get_metrics_dict()
            
            assert result == {"test": 42}
            mock_exporter.get_metrics_dict.assert_called_once()

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
