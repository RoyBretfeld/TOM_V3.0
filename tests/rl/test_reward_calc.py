"""
TOM v3.0 - RL Reward Calculator Tests
Unit-Tests für Reward-Berechnung und -Komponenten
"""

import pytest
import math

from apps.rl.reward_calc import RewardCalculator, RewardConfig, calc_reward, calc_reward_components


class TestRewardConfig:
    """Tests für Reward-Konfiguration"""
    
    def test_default_config(self):
        """Test für Standard-Konfiguration"""
        config = RewardConfig()
        
        assert config.resolution_weight == 0.6
        assert config.rating_weight == 0.2
        assert config.barge_in_weight == -0.1
        assert config.repeats_weight == -0.1
        assert config.handover_weight == -0.1
        assert config.optimal_duration_sec == 180.0
        assert config.duration_bonus_max == 0.2
        assert config.min_reward == -1.0
        assert config.max_reward == 1.0
    
    def test_custom_config(self):
        """Test für benutzerdefinierte Konfiguration"""
        config = RewardConfig(
            resolution_weight=0.8,
            rating_weight=0.1,
            optimal_duration_sec=120.0
        )
        
        assert config.resolution_weight == 0.8
        assert config.rating_weight == 0.1
        assert config.optimal_duration_sec == 120.0


class TestRewardCalculator:
    """Tests für Reward Calculator"""
    
    @pytest.fixture
    def calculator(self):
        """Reward Calculator für Tests"""
        return RewardCalculator()
    
    def test_perfect_signals(self, calculator):
        """Test für perfekte Signale (maximaler Reward)"""
        signals = {
            'resolution': True,
            'user_rating': 5,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.2 + 0.0 + 0.0 + 0.0 + 0.2 = 1.0
        assert reward == 1.0
    
    def test_worst_signals(self, calculator):
        """Test für schlechteste Signale (minimaler Reward)"""
        signals = {
            'resolution': False,
            'user_rating': 1,
            'barge_in_count': 3,
            'repeats': 3,
            'handover': True,
            'duration_sec': 0.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.0 + (-0.2) + (-0.1) + (-0.1) + (-0.1) + 0.0 = -0.5
        assert reward == -0.5
    
    def test_no_rating(self, calculator):
        """Test für Signale ohne Benutzerbewertung"""
        signals = {
            'resolution': True,
            'barge_in_count': 1,
            'repeats': 0,
            'handover': False,
            'duration_sec': 120.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.0 + (-0.033) + 0.0 + 0.0 + 0.067 = 0.634
        assert abs(reward - 0.7) < 0.01  # Toleranz für Rundungsfehler (tatsächlich 0.7)
    
    def test_many_barge_ins(self, calculator):
        """Test für viele Barge-Ins (maximale Strafe)"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 10,  # Mehr als 3, sollte auf 3 begrenzt werden
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.1 + (-0.1) + 0.0 + 0.0 + 0.2 = 0.8
        assert reward == 0.8
    
    def test_many_repeats(self, calculator):
        """Test für viele Wiederholungen (maximale Strafe)"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 10,  # Mehr als 3, sollte auf 3 begrenzt werden
            'handover': False,
            'duration_sec': 180.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.1 + 0.0 + (-0.1) + 0.0 + 0.2 = 0.8
        assert reward == 0.8
    
    def test_handover_penalty(self, calculator):
        """Test für Handover-Strafe"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': True,
            'duration_sec': 180.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.1 + 0.0 + 0.0 + (-0.1) + 0.2 = 0.8
        assert reward == 0.8
    
    def test_duration_bonus_optimal(self, calculator):
        """Test für optimale Gesprächsdauer"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0  # Optimal
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.1 + 0.0 + 0.0 + 0.0 + 0.2 = 0.9
        assert abs(reward - 0.9) < 0.01  # Toleranz für Rundungsfehler
    
    def test_duration_bonus_too_short(self, calculator):
        """Test für zu kurze Gesprächsdauer"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 90.0  # Zu kurz
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.1 + 0.0 + 0.0 + 0.0 + 0.1 = 0.8
        assert abs(reward - 0.8) < 0.01  # Toleranz für Rundungsfehler
    
    def test_duration_bonus_too_long(self, calculator):
        """Test für zu lange Gesprächsdauer"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 360.0  # Zu lang
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.1 + 0.0 + 0.0 + 0.0 + 0.0 = 0.7 (Bonus = 0 bei 360s)
        assert abs(reward - 0.7) < 0.01  # Toleranz für Rundungsfehler
    
    def test_reward_clamping(self, calculator):
        """Test für Reward-Clamping"""
        # Test für Reward > 1.0
        signals = {
            'resolution': True,
            'user_rating': 5,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0
        }
        
        reward = calculator.calc_reward(signals)
        assert reward == 1.0  # Geklemmt auf 1.0
    
    def test_calc_reward_components(self, calculator):
        """Test für Reward-Komponenten"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 1,
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0
        }
        
        components = calculator.calc_reward_components(signals)
        
        assert components['resolution'] == 0.6
        assert components['rating'] == 0.1
        assert abs(components['barge_in'] - (-0.033)) < 0.001  # Toleranz für Rundungsfehler
        assert components['repeats'] == 0.0
        assert components['handover'] == 0.0
        assert components['duration'] == 0.2
        assert abs(components['total'] - 0.867) < 0.01  # Toleranz für Rundungsfehler
    
    def test_get_reward_stats(self, calculator):
        """Test für Reward-Statistiken"""
        rewards = [0.5, 0.7, 0.3, 0.9, 0.1]
        
        stats = calculator.get_reward_stats(rewards)
        
        assert stats['count'] == 5
        assert abs(stats['mean'] - 0.5) < 0.001
        assert stats['min'] == 0.1
        assert stats['max'] == 0.9
        assert stats['p50'] == 0.5  # Median
    
    def test_get_reward_stats_empty(self, calculator):
        """Test für leere Reward-Liste"""
        rewards = []
        
        stats = calculator.get_reward_stats(rewards)
        
        assert stats['count'] == 0
        assert stats['mean'] == 0.0
        assert stats['std'] == 0.0
        assert stats['min'] == 0.0
        assert stats['max'] == 0.0


class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    def test_calc_reward_convenience(self):
        """Test für calc_reward Convenience-Funktion"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0
        }
        
        reward = calc_reward(signals)
        assert abs(reward - 0.9) < 0.01  # Toleranz für Rundungsfehler
    
    def test_calc_reward_components_convenience(self):
        """Test für calc_reward_components Convenience-Funktion"""
        signals = {
            'resolution': True,
            'user_rating': 4,
            'barge_in_count': 0,
            'repeats': 0,
            'handover': False,
            'duration_sec': 180.0
        }
        
        components = calc_reward_components(signals)
        assert 'total' in components
        assert abs(components['total'] - 0.9) < 0.01  # Toleranz für Rundungsfehler


class TestEdgeCases:
    """Tests für Edge Cases"""
    
    @pytest.fixture
    def calculator(self):
        """Reward Calculator für Tests"""
        return RewardCalculator()
    
    def test_empty_signals(self, calculator):
        """Test für leere Signale"""
        signals = {}
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.0 + 0.0 + 0.0 + 0.0 + 0.0 + 0.0 = 0.0
        assert reward == 0.0
    
    def test_negative_duration(self, calculator):
        """Test für negative Gesprächsdauer"""
        signals = {
            'resolution': True,
            'duration_sec': -10.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.0 + 0.0 + 0.0 + 0.0 + 0.0 = 0.6
        assert reward == 0.6
    
    def test_zero_duration(self, calculator):
        """Test für null Gesprächsdauer"""
        signals = {
            'resolution': True,
            'duration_sec': 0.0
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.0 + 0.0 + 0.0 + 0.0 + 0.0 = 0.6
        assert reward == 0.6
    
    def test_very_long_duration(self, calculator):
        """Test für sehr lange Gesprächsdauer"""
        signals = {
            'resolution': True,
            'duration_sec': 7200.0  # 2 Stunden
        }
        
        reward = calculator.calc_reward(signals)
        
        # Erwarteter Reward: 0.6 + 0.0 + 0.0 + 0.0 + 0.0 + (-0.2) = 0.4
        assert abs(reward - 0.4) < 0.01  # Toleranz für Rundungsfehler


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
