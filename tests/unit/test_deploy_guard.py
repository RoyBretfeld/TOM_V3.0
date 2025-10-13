"""
Tests für RL Deploy Guard
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
import json
import os
import tempfile
from apps.rl.deploy_guard import (
    DeployConfig, DeployGuard,
    select_variant_for_deployment, add_variant_to_deployment,
    remove_variant_from_deployment, get_deployment_status,
    get_variant_health
)

class TestDeployConfig:
    """Tests für DeployConfig"""
    
    def test_default_config(self):
        """Test Standard-Konfiguration"""
        config = DeployConfig()
        
        assert config.traffic_split_new == 0.1
        assert config.traffic_split_uncertain == 0.05
        assert config.base_variant == "v1a"
        assert config.blacklist_threshold == -0.2
        assert config.min_pulls_for_blacklist == 20
        assert config.min_pulls_for_confidence == 10
        assert config.confidence_threshold == 0.7
        assert config.max_active_variants == 12
        
    def test_custom_config(self):
        """Test benutzerdefinierte Konfiguration"""
        config = DeployConfig(
            traffic_split_new=0.2,
            base_variant="v2a",
            blacklist_threshold=-0.3
        )
        
        assert config.traffic_split_new == 0.2
        assert config.base_variant == "v2a"
        assert config.blacklist_threshold == -0.3

class TestDeployGuard:
    """Tests für DeployGuard"""
    
    def test_init_default(self):
        """Test Initialisierung mit Standard-Konfiguration"""
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuard()
            
            assert guard.config.traffic_split_new == 0.1
            assert guard.blacklisted_variants == set()
            assert guard.active_variants == {"v1a"}  # Base-Variante
            
    def test_init_custom_config(self):
        """Test Initialisierung mit benutzerdefinierter Konfiguration"""
        config = DeployConfig(base_variant="v2a", traffic_split_new=0.2)
        
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuard(config)
            
            assert guard.config.base_variant == "v2a"
            assert guard.config.traffic_split_new == 0.2
            assert guard.active_variants == {"v2a"}
            
    def test_load_state_file_exists(self):
        """Test Laden von existierendem State"""
        with tempfile.TemporaryDirectory() as temp_dir:
            state_file = os.path.join(temp_dir, 'deploy_state.json')
            os.makedirs(os.path.dirname(state_file), exist_ok=True)
            
            state_data = {
                'blacklisted_variants': ['v1b'],
                'active_variants': ['v1a', 'v2a'],
                'last_update': '2024-01-01T00:00:00'
            }
            
            with open(state_file, 'w') as f:
                json.dump(state_data, f)
                
            with patch('apps.rl.deploy_guard.os.path.exists', return_value=True):
                with patch('apps.rl.deploy_guard.open', mock_open(read_data=json.dumps(state_data))):
                    with patch('apps.rl.deploy_guard.PolicyBandit'):
                        guard = DeployGuard()
                        
                        assert guard.blacklisted_variants == {'v1b'}
                        assert guard.active_variants == {'v1a', 'v2a'}
                        
    def test_load_state_file_not_exists(self):
        """Test Laden wenn State-Datei nicht existiert"""
        with patch('apps.rl.deploy_guard.os.path.exists', return_value=False):
            with patch('apps.rl.deploy_guard.PolicyBandit'):
                guard = DeployGuard()
                
                assert guard.active_variants == {"v1a"}
                assert guard.blacklisted_variants == set()
                
    def test_save_state(self):
        """Test Speichern des States"""
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('apps.rl.deploy_guard.os.path.join') as mock_join:
                mock_join.return_value = os.path.join(temp_dir, 'deploy_state.json')
                
                with patch('apps.rl.deploy_guard.PolicyBandit'):
                    guard = DeployGuard()
                    guard.active_variants = {'v1a', 'v2a'}
                    guard.blacklisted_variants = {'v1b'}
                    
                    guard._save_state()
                    
                    # Prüfe ob Datei erstellt wurde
                    assert os.path.exists(os.path.join(temp_dir, 'deploy_state.json'))
                    
                    # Prüfe Inhalt
                    with open(os.path.join(temp_dir, 'deploy_state.json'), 'r') as f:
                        saved_data = json.load(f)
                        
                    assert set(saved_data['active_variants']) == {'v1a', 'v2a'}
                    assert set(saved_data['blacklisted_variants']) == {'v1b'}
                    
    def test_get_available_variants(self):
        """Test Ermittlung verfügbarer Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit.state.variants = {'v1a': None, 'v1b': None, 'v2a': None}
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuard()
            guard.blacklisted_variants = {'v1b'}
            
            available = guard._get_available_variants()
            assert set(available) == {'v1a', 'v2a'}
            
    def test_is_new_variant(self):
        """Test Erkennung neuer Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                # Neue Variante (weniger Pulls)
                mock_stats.return_value = {'pulls': 5}
                assert guard._is_new_variant('v1a') == True
                
                # Nicht neue Variante (genug Pulls)
                mock_stats.return_value = {'pulls': 15}
                assert guard._is_new_variant('v1a') == False
                
    def test_is_uncertain_variant(self):
        """Test Erkennung unsicherer Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                # Unsichere Variante (niedrige Konfidenz)
                mock_stats.return_value = {'pulls': 15, 'confidence': 0.5}
                assert guard._is_uncertain_variant('v1a') == True
                
                # Sichere Variante (hohe Konfidenz)
                mock_stats.return_value = {'pulls': 15, 'confidence': 0.8}
                assert guard._is_uncertain_variant('v1a') == False
                
                # Neue Variante (zu wenige Pulls)
                mock_stats.return_value = {'pulls': 5, 'confidence': 0.5}
                assert guard._is_uncertain_variant('v1a') == False
                
    def test_update_blacklist(self):
        """Test Blacklist-Update"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                with patch('apps.rl.deploy_guard.record_escalation') as mock_escalation:
                    with patch('apps.rl.deploy_guard.update_active_variants') as mock_update_active:
                        with patch('apps.rl.deploy_guard.update_blacklisted_variants') as mock_update_blacklisted:
                            with patch.object(guard, '_save_state') as mock_save:
                                # v1a sollte blacklisted werden (schlechter Reward)
                                mock_stats.side_effect = [
                                    {'pulls': 25, 'mean_reward': -0.3},  # v1a
                                    {'pulls': 15, 'mean_reward': 0.5}     # v2a
                                ]
                                
                                guard._update_blacklist()
                                
                                assert 'v1a' in guard.blacklisted_variants
                                assert 'v1a' not in guard.active_variants
                                assert 'v2a' in guard.active_variants
                                mock_escalation.assert_called_once_with('v1a')
                                mock_save.assert_called_once()
                                
    def test_select_variant_for_deployment_new(self):
        """Test Varianten-Auswahl für neue Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch.object(guard, '_get_available_variants', return_value=['v1a', 'v2a']):
                with patch.object(guard, '_is_new_variant') as mock_is_new:
                    with patch.object(guard, '_is_uncertain_variant', return_value=False):
                        with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                            with patch('apps.rl.deploy_guard.random') as mock_random:
                                mock_random.random.return_value = 0.05  # < 0.1 (traffic_split_new)
                                mock_random.choice.return_value = 'v2a'
                                
                                mock_is_new.side_effect = lambda v: v == 'v2a'
                                
                                selected = guard.select_variant_for_deployment()
                                
                                assert selected == 'v2a'
                                mock_record.assert_called_once_with('v2a')
                                
    def test_select_variant_for_deployment_uncertain(self):
        """Test Varianten-Auswahl für unsichere Varianten"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch.object(guard, '_get_available_variants', return_value=['v1a', 'v2a']):
                with patch.object(guard, '_is_new_variant', return_value=False):
                    with patch.object(guard, '_is_uncertain_variant') as mock_is_uncertain:
                        with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                            with patch('apps.rl.deploy_guard.random') as mock_random:
                                mock_random.random.return_value = 0.08  # < 0.1 + 0.05 (uncertain)
                                mock_random.choice.return_value = 'v2a'
                                
                                mock_is_uncertain.side_effect = lambda v: v == 'v2a'
                                
                                selected = guard.select_variant_for_deployment()
                                
                                assert selected == 'v2a'
                                mock_record.assert_called_once_with('v2a')
                                
    def test_select_variant_for_deployment_bandit(self):
        """Test Varianten-Auswahl durch Bandit"""
        with patch('apps.rl.deploy_guard.PolicyBandit') as mock_bandit_class:
            mock_bandit = Mock()
            mock_bandit.select.return_value = 'v2a'
            mock_bandit_class.return_value = mock_bandit
            
            guard = DeployGuard()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch.object(guard, '_get_available_variants', return_value=['v1a', 'v2a']):
                with patch.object(guard, '_is_new_variant', return_value=False):
                    with patch.object(guard, '_is_uncertain_variant', return_value=False):
                        with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                            with patch('apps.rl.deploy_guard.random') as mock_random:
                                mock_random.random.return_value = 0.5  # > 0.15 (new + uncertain)
                                
                                selected = guard.select_variant_for_deployment()
                                
                                assert selected == 'v2a'
                                mock_record.assert_called_once_with('v2a')
                                
    def test_select_variant_for_deployment_fallback(self):
        """Test Fallback zur Base-Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a'}
            
            with patch.object(guard, '_get_available_variants', return_value=[]):
                with patch('apps.rl.deploy_guard.record_policy_pull') as mock_record:
                    selected = guard.select_variant_for_deployment()
                    
                    assert selected == 'v1a'
                    mock_record.assert_called_once_with('v1a')
                    
    def test_add_variant_to_deployment_success(self):
        """Test erfolgreiches Hinzufügen einer Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a'}
            
            with patch('apps.rl.deploy_guard.update_active_variants') as mock_update:
                with patch.object(guard, '_save_state') as mock_save:
                    result = guard.add_variant_to_deployment('v2a')
                    
                    assert result == True
                    assert 'v2a' in guard.active_variants
                    mock_save.assert_called_once()
                    mock_update.assert_called_once_with(2)
                    
    def test_add_variant_to_deployment_blacklisted(self):
        """Test Hinzufügen einer blacklisted Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.blacklisted_variants = {'v2a'}
            
            result = guard.add_variant_to_deployment('v2a')
            
            assert result == False
            assert 'v2a' not in guard.active_variants
            
    def test_add_variant_to_deployment_max_reached(self):
        """Test Hinzufügen bei maximaler Anzahl Varianten"""
        config = DeployConfig(max_active_variants=1)
        
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard(config)
            guard.active_variants = {'v1a'}
            
            result = guard.add_variant_to_deployment('v2a')
            
            assert result == False
            assert 'v2a' not in guard.active_variants
            
    def test_remove_variant_from_deployment_success(self):
        """Test erfolgreiches Entfernen einer Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a', 'v2a'}
            
            with patch('apps.rl.deploy_guard.update_active_variants') as mock_update:
                with patch.object(guard, '_save_state') as mock_save:
                    result = guard.remove_variant_from_deployment('v2a')
                    
                    assert result == True
                    assert 'v2a' not in guard.active_variants
                    assert 'v1a' in guard.active_variants
                    mock_save.assert_called_once()
                    mock_update.assert_called_once_with(1)
                    
    def test_remove_variant_from_deployment_not_active(self):
        """Test Entfernen einer nicht aktiven Variante"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a'}
            
            result = guard.remove_variant_from_deployment('v2a')
            
            assert result == False
            assert 'v1a' in guard.active_variants
            
    def test_get_deployment_status(self):
        """Test Deployment-Status-Abfrage"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a', 'v2a'}
            guard.blacklisted_variants = {'v1b'}
            
            status = guard.get_deployment_status()
            
            assert status['active_variants'] == ['v1a', 'v2a']
            assert status['blacklisted_variants'] == ['v1b']
            assert status['total_active'] == 2
            assert status['total_blacklisted'] == 1
            assert 'config' in status
            
    def test_get_variant_health(self):
        """Test Varianten-Gesundheitsstatus"""
        with patch('apps.rl.deploy_guard.PolicyBandit'):
            guard = DeployGuard()
            guard.active_variants = {'v1a'}
            guard.blacklisted_variants = {'v1b'}
            
            with patch('apps.rl.deploy_guard.get_policy_stats') as mock_stats:
                mock_stats.return_value = {'pulls': 15, 'confidence': 0.8}
                
                # Aktive Variante
                health = guard.get_variant_health('v1a')
                assert health['is_active'] == True
                assert health['is_blacklisted'] == False
                assert health['health'] == 'stable'
                
                # Blacklisted Variante
                health = guard.get_variant_health('v1b')
                assert health['is_active'] == False
                assert health['is_blacklisted'] == True
                assert health['health'] == 'blacklisted'

class TestConvenienceFunctions:
    """Tests für Convenience-Funktionen"""
    
    def test_select_variant_for_deployment_convenience(self):
        """Test select_variant_for_deployment Convenience-Funktion"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.select_variant_for_deployment.return_value = 'v2a'
            mock_get_guard.return_value = mock_guard
            
            result = select_variant_for_deployment({'context': 'test'})
            
            assert result == 'v2a'
            mock_guard.select_variant_for_deployment.assert_called_once_with({'context': 'test'})
            
    def test_add_variant_to_deployment_convenience(self):
        """Test add_variant_to_deployment Convenience-Funktion"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.add_variant_to_deployment.return_value = True
            mock_get_guard.return_value = mock_guard
            
            result = add_variant_to_deployment('v2a')
            
            assert result == True
            mock_guard.add_variant_to_deployment.assert_called_once_with('v2a')
            
    def test_remove_variant_from_deployment_convenience(self):
        """Test remove_variant_from_deployment Convenience-Funktion"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.remove_variant_from_deployment.return_value = True
            mock_get_guard.return_value = mock_guard
            
            result = remove_variant_from_deployment('v2a')
            
            assert result == True
            mock_guard.remove_variant_from_deployment.assert_called_once_with('v2a')
            
    def test_get_deployment_status_convenience(self):
        """Test get_deployment_status Convenience-Funktion"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.get_deployment_status.return_value = {'test': 'status'}
            mock_get_guard.return_value = mock_guard
            
            result = get_deployment_status()
            
            assert result == {'test': 'status'}
            mock_guard.get_deployment_status.assert_called_once()
            
    def test_get_variant_health_convenience(self):
        """Test get_variant_health Convenience-Funktion"""
        with patch('apps.rl.deploy_guard._get_deploy_guard') as mock_get_guard:
            mock_guard = Mock()
            mock_guard.get_variant_health.return_value = {'health': 'stable'}
            mock_get_guard.return_value = mock_guard
            
            result = get_variant_health('v1a')
            
            assert result == {'health': 'stable'}
            mock_guard.get_variant_health.assert_called_once_with('v1a')

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
