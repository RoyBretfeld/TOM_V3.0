"""
TOM v3.0 - RL Policy Bandit Tests
Unit-Tests für Thompson Sampling und Policy-Auswahl
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from apps.rl.policy_bandit import PolicyBandit, PolicyVariant, BanditState, select_policy, update_policy_reward, get_policy_stats


class TestPolicyVariant:
    """Tests für Policy-Variante"""
    
    def test_policy_variant_creation(self):
        """Test für Policy-Variante Erstellung"""
        variant = PolicyVariant(
            id="v1a",
            name="Kurz und neutral",
            parameters={
                "greeting": "Hallo",
                "tone": "neutral",
                "length": "short"
            },
            description="Kurze, neutrale Begrüßung"
        )
        
        assert variant.id == "v1a"
        assert variant.name == "Kurz und neutral"
        assert variant.parameters["greeting"] == "Hallo"
        assert variant.parameters["tone"] == "neutral"
        assert variant.parameters["length"] == "short"
        assert variant.description == "Kurze, neutrale Begrüßung"


class TestBanditState:
    """Tests für Bandit-Zustand"""
    
    def test_bandit_state_creation(self):
        """Test für Bandit-Zustand Erstellung"""
        state = BanditState(
            alpha={"v1a": 2.0, "v1b": 1.5},
            beta={"v1a": 1.0, "v1b": 2.0},
            total_rewards={"v1a": 0.5, "v1b": -0.2},
            total_pulls={"v1a": 10, "v1b": 5},
            last_updated=1234567890.0
        )
        
        assert state.alpha["v1a"] == 2.0
        assert state.beta["v1b"] == 2.0
        assert state.total_rewards["v1a"] == 0.5
        assert state.total_pulls["v1b"] == 5
        assert state.last_updated == 1234567890.0


class TestPolicyBandit:
    """Tests für Policy Bandit"""
    
    @pytest.fixture
    def temp_state_file(self):
        """Temporäre Zustandsdatei für Tests"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            state_file = f.name
        
        yield state_file
        
        # Cleanup
        Path(state_file).unlink(missing_ok=True)
    
    @pytest.fixture
    def bandit(self, temp_state_file):
        """Policy Bandit für Tests"""
        return PolicyBandit(state_file=temp_state_file)
    
    @pytest.fixture
    def sample_variants(self):
        """Beispiel-Policy-Varianten"""
        return [
            PolicyVariant(
                id="v1a",
                name="Kurz und neutral",
                parameters={"greeting": "Hallo", "tone": "neutral", "length": "short"}
            ),
            PolicyVariant(
                id="v1b",
                name="Lang und freundlich",
                parameters={"greeting": "Guten Tag", "tone": "friendly", "length": "long"}
            ),
            PolicyVariant(
                id="v2a",
                name="Mittel und sachlich",
                parameters={"greeting": "Willkommen", "tone": "formal", "length": "medium"}
            )
        ]
    
    def test_bandit_initialization(self, bandit):
        """Test für Bandit-Initialisierung"""
        assert bandit.variants == {}
        assert bandit.state.alpha == {}
        assert bandit.state.beta == {}
        assert bandit.state.total_rewards == {}
        assert bandit.state.total_pulls == {}
    
    def test_add_variant(self, bandit, sample_variants):
        """Test für Hinzufügen von Policy-Varianten"""
        variant = sample_variants[0]
        bandit.add_variant(variant)
        
        assert variant.id in bandit.variants
        assert bandit.variants[variant.id] == variant
        assert bandit.state.alpha[variant.id] == 1.0
        assert bandit.state.beta[variant.id] == 1.0
        assert bandit.state.total_rewards[variant.id] == 0.0
        assert bandit.state.total_pulls[variant.id] == 0
    
    def test_add_multiple_variants(self, bandit, sample_variants):
        """Test für Hinzufügen mehrerer Policy-Varianten"""
        for variant in sample_variants:
            bandit.add_variant(variant)
        
        assert len(bandit.variants) == 3
        assert "v1a" in bandit.variants
        assert "v1b" in bandit.variants
        assert "v2a" in bandit.variants
    
    def test_select_without_variants(self, bandit):
        """Test für Auswahl ohne verfügbare Varianten"""
        with pytest.raises(ValueError):
            bandit.select()
    
    def test_select_with_variants(self, bandit, sample_variants):
        """Test für Policy-Auswahl"""
        for variant in sample_variants:
            bandit.add_variant(variant)
        
        # Teste mehrfache Auswahl
        selected_ids = []
        for _ in range(10):
            selected_id = bandit.select()
            selected_ids.append(selected_id)
            assert selected_id in ["v1a", "v1b", "v2a"]
        
        # Alle Varianten sollten mindestens einmal ausgewählt werden
        assert len(set(selected_ids)) > 1  # Mehr als eine Variante sollte ausgewählt werden
    
    def test_update_reward(self, bandit, sample_variants):
        """Test für Reward-Aktualisierung"""
        variant = sample_variants[0]
        bandit.add_variant(variant)
        
        # Initiale Werte
        initial_alpha = bandit.state.alpha[variant.id]
        initial_beta = bandit.state.beta[variant.id]
        initial_rewards = bandit.state.total_rewards[variant.id]
        initial_pulls = bandit.state.total_pulls[variant.id]
        
        # Update mit positivem Reward
        bandit.update(variant.id, 0.5)
        
        assert bandit.state.alpha[variant.id] > initial_alpha
        assert bandit.state.beta[variant.id] > initial_beta
        assert bandit.state.total_rewards[variant.id] == initial_rewards + 0.5
        assert bandit.state.total_pulls[variant.id] == initial_pulls + 1
    
    def test_update_negative_reward(self, bandit, sample_variants):
        """Test für negative Reward-Aktualisierung"""
        variant = sample_variants[0]
        bandit.add_variant(variant)
        
        # Update mit negativem Reward
        bandit.update(variant.id, -0.3)
        
        # Alpha sollte weniger stark steigen als Beta
        assert bandit.state.alpha[variant.id] > 1.0
        assert bandit.state.beta[variant.id] > 1.0
        assert bandit.state.total_rewards[variant.id] == -0.3
        assert bandit.state.total_pulls[variant.id] == 1
    
    def test_update_unknown_variant(self, bandit):
        """Test für Update mit unbekannter Variante"""
        # Sollte keine Exception werfen, nur Warning loggen
        bandit.update("unknown_variant", 0.5)
    
    def test_get_variant_stats(self, bandit, sample_variants):
        """Test für Varianten-Statistiken"""
        variant = sample_variants[0]
        bandit.add_variant(variant)
        
        # Initiale Statistiken
        stats = bandit.get_variant_stats(variant.id)
        assert stats['pulls'] == 0
        assert stats['total_reward'] == 0.0
        assert stats['mean_reward'] == 0.0
        assert stats['alpha'] == 1.0
        assert stats['beta'] == 1.0
        assert stats['confidence'] == 0.0  # Initial: 0 pulls, daher 0 confidence
        
        # Nach Updates
        bandit.update(variant.id, 0.5)
        bandit.update(variant.id, -0.2)
        
        stats = bandit.get_variant_stats(variant.id)
        assert stats['pulls'] == 2
        assert stats['total_reward'] == 0.3
        assert stats['mean_reward'] == 0.15
        assert stats['alpha'] > 1.0
        assert stats['beta'] > 1.0
    
    def test_get_variant_stats_unknown(self, bandit):
        """Test für Statistiken unbekannter Variante"""
        stats = bandit.get_variant_stats("unknown")
        assert stats == {}
    
    def test_get_all_stats(self, bandit, sample_variants):
        """Test für alle Statistiken"""
        for variant in sample_variants:
            bandit.add_variant(variant)
        
        all_stats = bandit.get_all_stats()
        
        assert len(all_stats) == 3
        assert "v1a" in all_stats
        assert "v1b" in all_stats
        assert "v2a" in all_stats
        
        # Alle sollten initiale Werte haben
        for variant_id in all_stats:
            stats = all_stats[variant_id]
            assert stats['pulls'] == 0
            assert stats['total_reward'] == 0.0
            assert stats['mean_reward'] == 0.0
    
    def test_get_exploration_rate(self, bandit, sample_variants):
        """Test für Exploration-Rate"""
        # Ohne Varianten
        assert bandit.get_exploration_rate() == 0.0
        
        # Mit Varianten
        for variant in sample_variants:
            bandit.add_variant(variant)
        
        exploration_rate = bandit.get_exploration_rate()
        assert 0.0 <= exploration_rate <= 1.0
        
        # Nach Updates sollte Exploration-Rate sinken
        bandit.update("v1a", 0.5)
        bandit.update("v1b", -0.2)
        
        new_exploration_rate = bandit.get_exploration_rate()
        assert new_exploration_rate < exploration_rate
    
    def test_reset_variant(self, bandit, sample_variants):
        """Test für Varianten-Reset"""
        variant = sample_variants[0]
        bandit.add_variant(variant)
        
        # Update mit Daten
        bandit.update(variant.id, 0.5)
        bandit.update(variant.id, -0.2)
        
        # Prüfe dass Daten vorhanden sind
        assert bandit.state.total_pulls[variant.id] == 2
        assert bandit.state.total_rewards[variant.id] == 0.3
        
        # Reset
        bandit.reset_variant(variant.id)
        
        # Prüfe dass Daten zurückgesetzt sind
        assert bandit.state.alpha[variant.id] == 1.0
        assert bandit.state.beta[variant.id] == 1.0
        assert bandit.state.total_rewards[variant.id] == 0.0
        assert bandit.state.total_pulls[variant.id] == 0
    
    def test_reset_unknown_variant(self, bandit):
        """Test für Reset unbekannter Variante"""
        # Sollte keine Exception werfen
        bandit.reset_variant("unknown_variant")
    
    def test_state_persistence(self, temp_state_file, sample_variants):
        """Test für Zustands-Persistierung"""
        # Erste Bandit-Instanz
        bandit1 = PolicyBandit(state_file=temp_state_file)
        for variant in sample_variants:
            bandit1.add_variant(variant)
        
        bandit1.update("v1a", 0.5)
        bandit1.update("v1b", -0.2)
        
        # Zweite Bandit-Instanz (lädt Zustand)
        bandit2 = PolicyBandit(state_file=temp_state_file)
        
        # Prüfe dass Zustand geladen wurde
        assert "v1a" in bandit2.state.alpha
        assert "v1b" in bandit2.state.alpha
        assert bandit2.state.total_pulls["v1a"] == 1
        assert bandit2.state.total_pulls["v1b"] == 1
        assert bandit2.state.total_rewards["v1a"] == 0.5
        assert bandit2.state.total_rewards["v1b"] == -0.2
    
    def test_state_persistence_corrupted_file(self, temp_state_file):
        """Test für korrupte Zustandsdatei"""
        # Schreibe korrupte JSON-Datei
        with open(temp_state_file, 'w') as f:
            f.write("invalid json content")
        
        # Bandit sollte trotzdem initialisiert werden
        bandit = PolicyBandit(state_file=temp_state_file)
        assert bandit.state.alpha == {}
        assert bandit.state.beta == {}


class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    @pytest.fixture
    def temp_state_file(self):
        """Temporäre Zustandsdatei für Tests"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            state_file = f.name
        
        yield state_file
        
        # Cleanup
        Path(state_file).unlink(missing_ok=True)
    
    def test_select_policy_convenience(self, temp_state_file):
        """Test für select_policy Convenience-Funktion"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_bandit.select.return_value = "v1a"
            
            result = select_policy({"profile": "kfz"})
            
            assert result == "v1a"
            mock_bandit.select.assert_called_once_with({"profile": "kfz"})
    
    def test_update_policy_reward_convenience(self, temp_state_file):
        """Test für update_policy_reward Convenience-Funktion"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            update_policy_reward("v1a", 0.5)
            
            mock_bandit.update.assert_called_once_with("v1a", 0.5)
    
    def test_get_policy_stats_convenience(self, temp_state_file):
        """Test für get_policy_stats Convenience-Funktion"""
        with patch('apps.rl.policy_bandit.policy_bandit') as mock_bandit:
            mock_stats = {"v1a": {"pulls": 10, "mean_reward": 0.3}}
            mock_bandit.get_all_stats.return_value = mock_stats
            
            result = get_policy_stats()
            
            assert result == mock_stats
            mock_bandit.get_all_stats.assert_called_once()


class TestThompsonSampling:
    """Tests für Thompson Sampling Algorithmus"""
    
    @pytest.fixture
    def temp_state_file(self):
        """Temporäre Zustandsdatei für Tests"""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            state_file = f.name
        
        yield state_file
        
        # Cleanup
        Path(state_file).unlink(missing_ok=True)
    
    def test_thompson_sampling_convergence(self, temp_state_file):
        """Test für Konvergenz von Thompson Sampling"""
        bandit = PolicyBandit(state_file=temp_state_file)
        
        # Füge zwei Varianten hinzu
        variant1 = PolicyVariant(id="v1a", name="Variant 1", parameters={})
        variant2 = PolicyVariant(id="v1b", name="Variant 2", parameters={})
        
        bandit.add_variant(variant1)
        bandit.add_variant(variant2)
        
        # Variante 1 bekommt bessere Rewards
        for _ in range(50):
            bandit.update("v1a", 0.7)  # Guter Reward
            bandit.update("v1b", 0.2)  # Schlechter Reward
        
        # Nach vielen Updates sollte v1a häufiger ausgewählt werden
        selections = []
        for _ in range(100):
            selected = bandit.select()
            selections.append(selected)
        
        v1a_count = selections.count("v1a")
        v1b_count = selections.count("v1b")
        
        # v1a sollte häufiger ausgewählt werden
        assert v1a_count > v1b_count
        assert v1a_count > 50  # Mehr als die Hälfte
    
    def test_thompson_sampling_exploration(self, temp_state_file):
        """Test für Exploration in Thompson Sampling"""
        bandit = PolicyBandit(state_file=temp_state_file)
        
        # Füge drei Varianten hinzu
        for i in range(3):
            variant = PolicyVariant(id=f"v{i+1}a", name=f"Variant {i+1}", parameters={})
            bandit.add_variant(variant)
        
        # Initiale Exploration-Rate sollte hoch sein
        initial_exploration = bandit.get_exploration_rate()
        assert initial_exploration > 0.05  # Niedrigere Schwelle
        
        # Nach Updates sollte Exploration sinken
        for variant_id in bandit.variants.keys():
            bandit.update(variant_id, 0.5)
        
        final_exploration = bandit.get_exploration_rate()
        assert final_exploration < initial_exploration


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
