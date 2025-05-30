from tests.base_test import BaseTest
from unittest.mock import MagicMock, patch
from utils.config_validator import validate_config
from PySide6.QtWidgets import QMessageBox

class TestConfigValidator(BaseTest):
    def setUp(self):
        """Set up test-specific fixtures"""
        super().setUp()
        self.mock_config = MagicMock()
        
    def test_valid_config(self):
        """Test validation with valid configuration"""
        self.mock_config.is_configured = "True"
        
        with patch('PySide6.QtWidgets.QMessageBox') as mock_msgbox:
            result = validate_config(self.mock_config)
            
            self.assertTrue(result)
            mock_msgbox.warning.assert_not_called()
            self.mock_log_error.assert_not_called()
            
    def test_invalid_config(self):
        """Test validation with invalid configuration"""
        self.mock_config.is_configured = "False"
        
        with patch('PySide6.QtWidgets.QMessageBox') as mock_msgbox:
            result = validate_config(self.mock_config)
            
            self.assertFalse(result)
            mock_msgbox.warning.assert_called_once()
            self.mock_log_error.assert_called_once_with("RevEng.AI | Configuration is missing or incomplete")
            
    def test_none_config(self):
        """Test validation with None configuration"""
        with patch('PySide6.QtWidgets.QMessageBox') as mock_msgbox:
            result = validate_config(None)
            
            self.assertFalse(result)
            mock_msgbox.warning.assert_called_once()
            self.mock_log_error.assert_called_once_with("RevEng.AI | Configuration is missing or incomplete")
            
    def test_message_box_content(self):
        """Test that the warning message box has correct content"""
        self.mock_config.is_configured = "False"
        
        with patch('PySide6.QtWidgets.QMessageBox') as mock_msgbox:
            validate_config(self.mock_config)
            
            mock_msgbox.warning.assert_called_once_with(
                None,
                "RevEng.AI Configuration Required",
                "Please configure your RevEng.AI API key and host before uploading.\n\n"
                "You can do this through:\nRevEng.AI > Configure",
                QMessageBox.Ok
            )

if __name__ == '__main__':
    unittest.main() 