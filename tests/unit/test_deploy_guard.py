"""
Tests für RL Deploy Guard
"""

import pytest
from unittest.mock import patch, mock_open, Mock, MagicMock
import json
import os
import tempfile
from apps.rl.deploy_guard import (
    DeployConfig, DeployGuard, DeployGuardFull, DeployState,
    load_state, save_state, maybe_blacklist,
    select_variant_for_deployment, add_variant_to_deployment,
    remove_variant_from_deployment, get_deployment_status, get_variant_health
)

class TestDeployConfig:
    """Tests für DeployConfig"""
    
    def test_default_config(self):
        """Test Standard-Konfiguration"""
        config = DeployConfig()
        assert config.base_variant == "v1a"
        assert config.traffic_split_new == 0.1
        assert config.traffic_split_uncertain == 0.2
        assert config.blacklist_threshold_reward == -0.2
        assert config.min_pulls_for_evaluation == 20
        assert config.max_active_variants == 5

    def test_custom_config(self):
        """Test benutzerdefinierte Konfiguration"""
        config = DeployConfig(
            base_variant="v2a",
            traffic_split_new=0.15,
            traffic_split_uncertain=0.25,
            blacklist_threshold_reward=-0.3,
            min_pulls_for_evaluation=30,
            max_active_variants=3
        )
        assert config.base_variant == "v2a"
        assert config.traffic_split_new == 0.15
        assert config.traffic_split_uncertain == 0.25
        assert config.blacklist_threshold_reward == -0.3
        assert config.min_pulls_for_evaluation == 30
        assert config.max_active_variants == 3

class TestDeployGuard:
    """Tests für DeployGuard (vereinfachte Version)"""
    
    def test_init_custom_config(self):
        """Test Initialisierung mit benutzerdefinierter Konfiguration"""
        g = DeployGuard.from_config({"variants": ["v2a"], "base_variant":"v2a"})
        assert g.base_variant == "v2a"
        assert g.variants == {"v2a"}
        assert g.blacklist == set()

    def test_pick_variant_deterministic(self):
        """Test deterministische Varianten-Auswahl"""
        class DummyRNG:
            def choice(self, seq): return seq[0]
        
        g = DeployGuard(["v1a","v2a"], "v1a", rng=DummyRNG())
        assert g.pick_variant(["v2a","v1a"]) == "v2a"

    def test_get_eligible(self):
        """Test verfügbare Varianten"""
        g = DeployGuard(["v1a","v2a","v3a"], "v1a")
        g.blacklist.add("v3a")
        eligible = g.get_eligible()
        assert eligible == ["v2a"]  # Sortiert, ohne v1a (base) und v3a (blacklisted)

    def test_get_deployment_status_ordered(self):
        """Test Deployment-Status mit sortierten Listen"""
        g = DeployGuard(["v3a","v1a","v2a"], "v1a")
        g.blacklist.update({"v3a"})
        st = g.get_deployment_status()
        assert st["variants"] == ["v1a","v2a","v3a"]
        assert st["blacklist"] == ["v3a"]
        assert st["eligible"] == ["v2a"]

class TestDeployGuardFull:
    """Tests für DeployGuardFull (vollständige Version)"""
    
    def test_init_default(self):
        """Test Standard-Initialisierung"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            assert guard.config.base_variant == "v1a"
            assert guard.config.traffic_split_new == 0.1
            assert guard.config.traffic_split_uncertain == 0.2
            assert guard.config.blacklist_threshold_reward == -0.2
            assert guard.config.min_pulls_for_evaluation == 20
            assert guard.config.max_active_variants == 5

    def test_init_custom_config(self):
        """Test Initialisierung mit benutzerdefinierter Konfiguration"""
        config = DeployConfig(base_variant="v2a", traffic_split_new=0.2)
        
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit_class.return_value = mock_bandit
            
            with patch.object(DeployGuardFull, '_load_state') as mock_load_state:
                mock_load_state.return_value = None  # Kein State laden
                
                guard = DeployGuardFull(config)
                
                assert guard.config.base_variant == "v2a"
                assert guard.config.traffic_split_new == 0.2
                assert guard.active_variants == {"v2a"}

    def test_load_state_file_exists(self):
        """Test Laden von existierendem State"""
        state_data = {
            'blacklisted_variants': ['v1b'],
            'active_variants': ['v1a', 'v2a'],
            'last_update': '2024-01-01T00:00:00'
        }
        
        with patch('apps.rl.deploy_guard.os.path.exists', return_value=True):
            with patch('apps.rl.deploy_guard.open', mock_open(read_data=json.dumps(state_data))):
                with patch('apps.rl.deploy_guard.PolicyBandit'):
                    guard = DeployGuardFull()
                    assert 'v1b' in guard.blacklisted_variants
                    assert 'v1a' in guard.active_variants
                    assert 'v2a' in guard.active_variants

    def test_load_state_file_not_exists(self):
        """Test Laden von nicht existierendem State"""
        with patch('apps.rl.deploy_guard.os.path.exists', return_value=False):
            with patch('apps.rl.deploy_guard.PolicyBandit'):
                guard = DeployGuardFull()
                assert guard.active_variants == {"v1a"}  # Basis-Variante
                assert guard.blacklisted_variants == set()

    def test_save_state(self):
        """Test Speichern des States"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, 'deploy_state.json')
            
            with patch('apps.rl.deploy_guard.PolicyBandit'):
                guard = DeployGuardFull(state_file=state_file)
                guard.active_variants.add("v2a")
                guard._save_state()
                
                # Prüfe, ob Datei erstellt wurde
                assert os.path.exists(state_file)

    def test_get_available_variants(self):
        """Test verfügbare Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit.state.variants = {'v1a': Mock(), 'v2a': Mock(), 'v3a': Mock()}
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuardFull()
            guard.blacklisted_variants = {'v3a'}
            
            available = guard._get_available_variants()
            assert 'v1a' in available
            assert 'v2a' in available
            assert 'v3a' not in available

    def test_is_new_variant(self):
        """Test Erkennung neuer Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'v2a': {'pulls': 5}}  # Weniger als min_pulls_for_evaluation
                
                assert guard._is_new_variant('v2a') == True
                
                mock_stats.return_value = {'v2a': {'pulls': 25}}  # Mehr als min_pulls_for_evaluation
                assert guard._is_new_variant('v2a') == False

    def test_is_uncertain_variant(self):
        """Test Erkennung unsicherer Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'v2a': {'pulls': 25, 'confidence': 0.4}}  # Niedrige Konfidenz
                
                assert guard._is_uncertain_variant('v2a') == True
                
                mock_stats.return_value = {'v2a': {'pulls': 25, 'confidence': 0.8}}  # Hohe Konfidenz
                assert guard._is_uncertain_variant('v2a') == False

    def test_update_blacklist(self):
        """Test Blacklist-Update"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                with patch('apps.rl.deploy_guard.record_escalation') as mock_escalation:
                    with patch('apps.rl.deploy_guard.update_active_variants') as mock_update_active:
                        with patch('apps.rl.deploy_guard.update_blacklisted_variants') as mock_update_blacklisted:
                            with patch.object(guard, '_save_state') as mock_save:
                                # v2a sollte blacklisted werden (schlechter Reward)
                                mock_stats.return_value = {
                                    'v1a': {'pulls': 15, 'mean_reward': 0.5},     # Basis (wird übersprungen)
                                    'v2a': {'pulls': 25, 'mean_reward': -0.3}      # Sollte blacklisted werden
                                }
                                
                                guard._update_blacklist()
                                
                                assert 'v2a' in guard.blacklisted_variants
                                assert 'v2a' not in guard.active_variants
                                assert 'v1a' in guard.active_variants  # Basis-Variante bleibt

    def test_select_variant_for_deployment_new(self):
        """Test Varianten-Auswahl für neue Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'v1a': {'pulls': 25}, 'v2a': {'pulls': 5}}
                
                with patch.object(guard, '_get_available_variants', return_value=['v1a', 'v2a']):
                    with patch.object(guard, '_is_uncertain_variant', return_value=False):
                        with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                            with patch('apps.rl.deploy_guard._random') as mock_random:
                                mock_random.random.return_value = 0.05  # Unter Traffic-Split-Schwelle
                                mock_random.choice.return_value = 'v2a'
                            
                                selected = guard.select_variant_for_deployment()
                            
                                assert selected == 'v2a'
                                mock_record.assert_called_once_with('TOM', 'general', 'v2a')

    def test_select_variant_for_deployment_uncertain(self):
        """Test Varianten-Auswahl für unsichere Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch.object(guard, '_get_available_variants', return_value=['v1a', 'v2a']):
                with patch.object(guard, '_is_new_variant', return_value=False):
                    with patch.object(guard, '_is_uncertain_variant') as mock_is_uncertain:
                        with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                            with patch('apps.rl.deploy_guard._random') as mock_random:
                                mock_is_uncertain.return_value = True
                                mock_random.random.return_value = 0.03  # Unter Traffic-Split-Schwelle
                                mock_random.choice.return_value = 'v2a'
                                
                                selected = guard.select_variant_for_deployment()
                                
                                assert selected == 'v2a'
                                mock_record.assert_called_once_with('TOM', 'general', 'v2a')

    def test_select_variant_for_deployment_bandit(self):
        """Test Varianten-Auswahl durch Bandit"""
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit.select.return_value = 'v2a'
            mock_bandit.state.variants = {'v1a': Mock(), 'v2a': Mock()}
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuardFull()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'v1a': {'pulls': 25, 'confidence': 0.8}, 'v2a': {'pulls': 25, 'confidence': 0.8}}
                
                with patch.object(guard, '_get_available_variants', return_value=['v1a', 'v2a']):
                    with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                        with patch('apps.rl.deploy_guard._random') as mock_random:
                            mock_random.random.side_effect = [0.5, 0.5]  # Über Traffic-Split-Schwellen
                            
                            selected = guard.select_variant_for_deployment()
                            
                            assert selected == 'v2a'
                            mock_record.assert_called_once_with('TOM', 'general', 'v2a')

    def test_select_variant_for_deployment_fallback(self):
        """Test Fallback zur Base-Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit.select.return_value = 'v1a'
            mock_bandit.state.variants = {'v1a': Mock()}
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuardFull()
            guard.active_variants = set()  # Keine aktiven Varianten außer Basis
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'v1a': {'pulls': 25, 'confidence': 0.8}}
                
                with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                    selected = guard.select_variant_for_deployment()
                    
                    assert selected == 'v1a'
                    mock_record.assert_called_once_with('TOM', 'general', 'v1a')

    def test_add_variant_to_deployment_success(self):
        """Test erfolgreiches Hinzufügen einer Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            
            result = guard.add_variant_to_deployment('v2a')
            
            assert result == True
            assert 'v2a' in guard.active_variants

    def test_add_variant_to_deployment_blacklisted(self):
        """Test Hinzufügen einer blacklisted Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.blacklisted_variants.add('v2a')
            guard.active_variants.discard('v2a')  # Entferne v2a falls vorhanden
            
            result = guard.add_variant_to_deployment('v2a')
            
            assert result == False
            assert 'v2a' not in guard.active_variants

    def test_add_variant_to_deployment_max_reached(self):
        """Test Hinzufügen bei maximaler Anzahl"""
        config = DeployConfig(max_active_variants=1)
        
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull(config)
            guard.active_variants.add('v2a')  # Bereits eine zusätzliche Variante
            
            result = guard.add_variant_to_deployment('v3a')
            
            assert result == False
            assert 'v3a' not in guard.active_variants

    def test_remove_variant_from_deployment_success(self):
        """Test erfolgreiches Entfernen einer Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.active_variants.add('v2a')
            
            result = guard.remove_variant_from_deployment('v2a')
            
            assert result == True
            assert 'v2a' not in guard.active_variants

    def test_remove_variant_from_deployment_not_active(self):
        """Test Entfernen einer nicht aktiven Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            
            result = guard.remove_variant_from_deployment('v2a')
            
            assert result == False

    def test_get_deployment_status(self):
        """Test Deployment-Status-Abfrage"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.active_variants = {'v1a', 'v2a'}
            guard.blacklisted_variants = {'v1b'}
            
            status = guard.get_deployment_status()
            
            assert sorted(status['active_variants']) == sorted(['v1a', 'v2a'])
            assert sorted(status['blacklisted_variants']) == sorted(['v1b'])
            assert status['base_variant'] == 'v1a'
            assert 'last_update' in status
            assert 'config' in status

    def test_get_variant_health(self):
        """Test Varianten-Gesundheitsabfrage"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuardFull()
            guard.active_variants.add('v2a')
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'pulls': 10, 'confidence': 0.7}
                
                health = guard.get_variant_health('v2a')
                
                assert health['id'] == 'v2a'
                assert health['is_active'] == True
                assert health['is_blacklisted'] == False
                assert health['is_new'] == True  # Weniger als 20 Pulls
                assert health['is_uncertain'] == False  # Konfidenz > 0.6
                assert 'stats' in health

class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    def test_select_variant_for_deployment_convenience(self):
        """Test Convenience-Funktion für Varianten-Auswahl"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.select_variant_for_deployment.return_value = 'v2a'
            mock_get_guard.return_value = mock_guard
            
            result = select_variant_for_deployment({'profile': 'kfz'})
            
            assert result == 'v2a'
            mock_guard.select_variant_for_deployment.assert_called_once_with({'profile': 'kfz'})

    def test_add_variant_to_deployment_convenience(self):
        """Test Convenience-Funktion für Varianten-Hinzufügung"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.add_variant_to_deployment.return_value = True
            mock_get_guard.return_value = mock_guard
            
            result = add_variant_to_deployment('v2a')
            
            assert result == True
            mock_guard.add_variant_to_deployment.assert_called_once_with('v2a')

    def test_remove_variant_from_deployment_convenience(self):
        """Test Convenience-Funktion für Varianten-Entfernung"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.remove_variant_from_deployment.return_value = True
            mock_get_guard.return_value = mock_guard
            
            result = remove_variant_from_deployment('v2a')
            
            assert result == True
            mock_guard.remove_variant_from_deployment.assert_called_once_with('v2a')

    def test_get_deployment_status_convenience(self):
        """Test Convenience-Funktion für Status-Abfrage"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.get_deployment_status.return_value = {'status': 'active'}
            mock_get_guard.return_value = mock_guard
            
            result = get_deployment_status()
            
            assert result == {'status': 'active'}
            mock_guard.get_deployment_status.assert_called_once()

    def test_get_variant_health_convenience(self):
        """Test Convenience-Funktion für Gesundheitsabfrage"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.get_variant_health.return_value = {'health': 'good'}
            mock_get_guard.return_value = mock_guard
            
            result = get_variant_health('v2a')
            
            assert result == {'health': 'good'}
            mock_guard.get_variant_health.assert_called_once_with('v2a')

class TestUtilityFunctions:
    """Tests für Utility-Funktionen"""
    
    def test_load_state_empty_ok(self):
        """Test Laden von leerer Datei"""
        with patch('apps.rl.deploy_guard.open', mock_open(read_data="")):
            assert load_state("x.json") == {}

    def test_load_state_valid_json(self):
        """Test Laden von gültigem JSON"""
        with patch('apps.rl.deploy_guard.open', mock_open(read_data='{"a":1}')):
            assert load_state("x.json") == {"a":1}

    def test_load_state_file_not_found(self):
        """Test Laden von nicht existierender Datei"""
        with patch('apps.rl.deploy_guard.open', side_effect=FileNotFoundError):
            assert load_state("nonexistent.json") == {}

    def test_save_state(self):
        """Test Speichern des States"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, 'test_state.json')
            
            test_data = {"test": "data"}
            save_state(state_file, test_data)
            
            # Prüfe, ob Datei erstellt wurde
            assert os.path.exists(state_file)
            
            # Prüfe Inhalt
            with open(state_file, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            assert loaded_data == test_data

    def test_maybe_blacklist(self):
        """Test Blacklist-Logik"""
        class DummyStats:
            def get_policy_stats(self, variant): 
                return {"samples": 25, "reward_mean": -0.25}
        
        g = DeployGuard(["v1a","v2a"], "v1a")
        maybe_blacklist(g, "v2a", DummyStats())
        assert "v2a" in g.blacklist

    def test_maybe_blacklist_base_variant(self):
        """Test dass Basis-Variante nie blacklisted wird"""
        class DummyStats:
            def get_policy_stats(self, variant): 
                return {"samples": 25, "reward_mean": -0.25}
        
        g = DeployGuard(["v1a","v2a"], "v1a")
        maybe_blacklist(g, "v1a", DummyStats())  # Basis-Variante
        assert "v1a" not in g.blacklist