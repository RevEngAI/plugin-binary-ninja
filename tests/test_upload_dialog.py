from tests.base_test import BaseTest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QDialog, QMessageBox
from features.upload.upload_dialog import UploadDialog

class TestUploadDialog(BaseTest):
    def setUp(self):
        """Set up test-specific fixtures"""
        super().setUp()
        self.mock_config = MagicMock()
        self.mock_uploader = MagicMock()
        self.mock_bv = MagicMock()
        
    def test_dialog_initialization(self):
        """Test dialog initialization"""
        dialog = UploadDialog(self.mock_config, self.mock_uploader, self.mock_bv)
        
        self.assertIsInstance(dialog, QDialog)
        self.assertEqual(dialog.config, self.mock_config)
        self.assertEqual(dialog.uploader, self.mock_uploader)
        self.assertEqual(dialog.bv, self.mock_bv)
        
    def test_upload_options(self):
        """Test getting upload options"""
        dialog = UploadDialog(self.mock_config, self.mock_uploader, self.mock_bv)
        
        # Set some test values
        dialog.debug_combo.setCurrentText("test.pdb")
        dialog.tags_input.setText("test,debug")
        dialog.model_combo.setCurrentText("test_model")
        dialog.private_radio.setChecked(True)
        
        options = dialog.get_upload_options()
        
        self.assertEqual(options["debug_info"], "test.pdb")
        self.assertEqual(options["tags"], ["test", "debug"])
        self.assertEqual(options["model"], "test_model")
        self.assertTrue(options["is_private"])
        
    def test_upload_binary_success(self):
        """Test successful binary upload"""
        dialog = UploadDialog(self.mock_config, self.mock_uploader, self.mock_bv)
        self.mock_uploader.upload_binary.return_value = True
        
        # Start the save thread
        dialog.save_thread = MagicMock()
        dialog.upload_binary()
            
        # Verify thread was started
        dialog.save_thread.start.assert_called_once()
            
    def test_upload_binary_validation(self):
        """Test binary upload validation"""
        dialog = UploadDialog(self.mock_config, self.mock_uploader, self.mock_bv)
        
        # Test with invalid model selection
        dialog.model_combo.setCurrentText("")
        with patch('PySide6.QtWidgets.QMessageBox') as mock_msgbox:
            dialog.upload_binary()
            mock_msgbox.warning.assert_called_once()
            self.mock_log_warn.assert_called_once_with("RevEng.AI | Model selection is required")
            
    def test_model_loading(self):
        """Test model loading in combo box"""
        # Mock the uploader to return some test models
        test_models = {"model1", "model2", "model3"}
        self.mock_uploader.get_models.return_value = test_models
        
        dialog = UploadDialog(self.mock_config, self.mock_uploader, self.mock_bv)
        
        # Check that all models were added to combo box
        self.assertEqual(dialog.model_combo.count(), len(test_models))
        combo_items = {dialog.model_combo.itemText(i) for i in range(dialog.model_combo.count())}
        self.assertEqual(combo_items, test_models)
        
    def test_tag_parsing(self):
        """Test tag parsing from input"""
        dialog = UploadDialog(self.mock_config, self.mock_uploader, self.mock_bv)
        
        # Test various tag input formats
        test_cases = [
            ("tag1,tag2,tag3", ["tag1", "tag2", "tag3"]),
            ("tag1, tag2, tag3", ["tag1", "tag2", "tag3"]),
            ("single", ["single"]),
            ("", []),
            (" , , ", []),
        ]
        
        for input_text, expected_tags in test_cases:
            dialog.tags_input.setText(input_text)
            options = dialog.get_upload_options()
            self.assertEqual(options["tags"], expected_tags)

if __name__ == '__main__':
    unittest.main() 