import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
import sys

class BaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up any test class-wide fixtures here"""
        # Create QApplication instance if it doesn't exist
        if not QApplication.instance():
            cls.app = QApplication(sys.argv)
        else:
            cls.app = QApplication.instance()
            
    def setUp(self):
        """Set up any test-specific fixtures here"""
        # Create common mocks that might be needed across tests
        self.mock_bv = MagicMock()  # Mock BinaryView
        self.mock_settings = MagicMock()  # Mock Settings
        
        # Set up patches
        self.settings_patcher = patch('binaryninja.Settings', return_value=self.mock_settings)
        self.log_info_patcher = patch('binaryninja.log_info')
        self.log_error_patcher = patch('binaryninja.log_error')
        self.log_warn_patcher = patch('binaryninja.log_warn')
        
        # Start patches
        self.mock_settings_class = self.settings_patcher.start()
        self.mock_log_info = self.log_info_patcher.start()
        self.mock_log_error = self.log_error_patcher.start()
        self.mock_log_warn = self.log_warn_patcher.start()
        
    def tearDown(self):
        """Clean up any test-specific fixtures here"""
        # Stop all patches
        self.settings_patcher.stop()
        self.log_info_patcher.stop()
        self.log_error_patcher.stop()
        self.log_warn_patcher.stop()
        
    @classmethod
    def tearDownClass(cls):
        """Clean up any test class-wide fixtures here"""
        if hasattr(cls, 'app'):
            cls.app.quit() 