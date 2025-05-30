from .base_test import BaseTest
from unittest.mock import MagicMock, patch
from features.configuration import ConfigurationFeature
from features.configuration.config import Config

class TestConfiguration(BaseTest):
    def setUp(self):
        """Set up test-specific fixtures"""
        super().setUp()
        self.feature = ConfigurationFeature()
        
    def test_initialization(self):
        """Test configuration feature initialization"""
        self.assertIsInstance(self.feature.config, Config)
        self.mock_log_info.assert_called_with("RevEng.AI | Configuration Feature initialized")
        
    def test_register_command(self):
        """Test command registration"""
        with patch('binaryninja.PluginCommand') as mock_command:
            self.feature._register_command()
            
            mock_command.register.assert_called_once_with(
                "RevEng.AI\\Configure",
                "Configure RevEng.AI settings",
                self.feature.show_configuration
            )
            
    def test_show_configuration(self):
        """Test configuration dialog display"""
        mock_wizard = MagicMock()
        with patch('features.configuration.config_dialog.ConfigDialog', return_value=mock_wizard):
            self.feature.show_configuration(self.mock_bv)
            
            self.mock_log_info.assert_called_with("RevEng.AI | Opening configuration wizard")
            mock_wizard.exec_.assert_called_once()
            
    def test_get_config(self):
        """Test config getter"""
        config = self.feature.get_config()
        self.assertIsInstance(config, Config)
        self.assertEqual(config, self.feature.config)
        
class TestConfig(BaseTest):
    def setUp(self):
        """Set up test-specific fixtures"""
        super().setUp()
        self.config = Config()
        
    def test_initialization(self):
        """Test config initialization"""
        self.assertEqual(self.config.api_key, "")
        self.assertEqual(self.config.host, "")
        self.assertIsNone(self.config.current_analysis)
        self.assertEqual(self.config.is_configured, "False")
        
    def test_save_config_success(self):
        """Test successful config save"""
        self.config.api_key = "test_key"
        self.config.host = "test_host"
        
        with patch('reait.api.RE_authentication') as mock_auth:
            success = self.config.save_config()
            
            self.assertTrue(success)
            self.assertEqual(self.config.is_configured, "True")
            mock_auth.assert_called_once()
            
    def test_save_config_failure(self):
        """Test failed config save"""
        self.config.api_key = "invalid_key"
        self.config.host = "invalid_host"
        
        with patch('reait.api.RE_authentication', side_effect=Exception("Auth failed")):
            success = self.config.save_config()
            
            self.assertFalse(success)
            self.assertEqual(self.config.is_configured, "False")
            self.mock_log_info.assert_called_with("RevEng.AI | Failed to save API key: Auth failed")
            
    def test_clear_config(self):
        """Test config clearing"""
        # Set some initial values
        self.config.api_key = "test_key"
        self.config.host = "test_host"
        self.config.current_analysis = "test_analysis"
        self.config.is_configured = "True"
        
        # Clear config
        self.config.clear_config()
        
        # Verify values are cleared
        self.assertEqual(self.config.api_key, "")
        self.assertEqual(self.config.host, "")
        self.assertIsNone(self.config.current_analysis)
        self.assertEqual(self.config.is_configured, "False") 