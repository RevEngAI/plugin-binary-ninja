from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QRadioButton, QButtonGroup,
                              QLineEdit, QGroupBox, QFileDialog, QProgressDialog, QMessageBox)
from PySide6.QtCore import Qt, QThread, Signal
from binaryninja import log_info, log_error, log_warn

class ModelLoadThread(QThread):
    finished = Signal(set)  # Signal emitting the loaded models
    error = Signal(str)     # Signal for error handling
    
    def __init__(self, uploader):
        super().__init__()
        self.uploader = uploader
        
    def run(self):
        try:
            models = self.uploader.get_models()
            self.finished.emit(models)
        except Exception as e:
            log_error(f"RevEng.AI | Failed to load models: {str(e)}")
            self.error.emit(str(e))

class UploadBinaryThread(QThread):
    finished = Signal(bool, str)  # Signal for success/failure and error message
    
    def __init__(self, uploader, bv, options):
        super().__init__()
        self.uploader = uploader
        self.bv = bv
        self.options = options
        
    def run(self):
        try:
            success = self.uploader.upload_binary(self.bv, self.options)
            if success:
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "Failed to upload binary")
        except Exception as e:
            self.finished.emit(False, str(e))

class UploadDialog(QDialog):
    def __init__(self, config, uploader, bv):
        super().__init__()
        self.config = config
        self.uploader = uploader
        self.bv = bv
        self.model_thread = None
        self.upload_thread = None
        self.progress = None
        self.load_models()
        self.init_ui()
        
        
    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Process Binary")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        debug_layout = QHBoxLayout()
        debug_label = QLabel("Debug Info or PDB:")
        self.debug_combo = QComboBox()
        self.debug_combo.setEditable(True)

        debug_browse = QPushButton("...")
        debug_browse.setMaximumWidth(30)
        debug_browse.clicked.connect(self.browse_debug_info)
        
        debug_layout.addWidget(debug_label)
        debug_layout.addWidget(self.debug_combo)
        debug_layout.addWidget(debug_browse)
        layout.addLayout(debug_layout)
        
        tags_layout = QHBoxLayout()
        tags_label = QLabel("Custom Tags (format: tag,tag):")
        self.tags_input = QLineEdit()
        tags_layout.addWidget(tags_label)
        tags_layout.addWidget(self.tags_input)
        layout.addLayout(tags_layout)
        
        model_layout = QHBoxLayout()
        model_label = QLabel("AI Model:")
        self.model_combo = QComboBox()
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)
        
        privacy_group = QGroupBox("Privacy:")
        privacy_layout = QVBoxLayout()
        
        self.privacy_group = QButtonGroup()
        self.private_radio = QRadioButton("Private to you")
        self.public_radio = QRadioButton("Public access")
        self.private_radio.setChecked(True)
        
        self.privacy_group.addButton(self.private_radio)
        self.privacy_group.addButton(self.public_radio)
        
        privacy_layout.addWidget(self.private_radio)
        privacy_layout.addWidget(self.public_radio)
        privacy_group.setLayout(privacy_layout)
        layout.addWidget(privacy_group)
        
        button_layout = QHBoxLayout()
        self.process_button = QPushButton("Process")
        self.process_button.clicked.connect(self.upload_binary)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.process_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def load_models(self):
        """Start loading models in background"""
        # Create and show progress dialog
        self.progress = QProgressDialog("Loading available models...", None, 0, 0, self)
        self.progress.setWindowTitle("RevEng.AI")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setCancelButton(None)
        self.progress.setMinimumWidth(400)
        self.progress.setMinimumHeight(100)
        self.progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                color: black;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
                min-width: 250px;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
            QLabel {
                color: black;
                font-size: 13px;
                padding: 10px;
            }
        """)
        
        self.model_thread = ModelLoadThread(self.uploader)
        self.model_thread.finished.connect(self._on_models_loaded)
        self.model_thread.error.connect(self._on_model_load_error)
        self.model_thread.start()
        
        self.progress.show()
        
    def _on_models_loaded(self, models):
        """Handle successful model loading"""
        self.progress.close()
        self.model_combo.clear()
        for model in sorted(models):
            self.model_combo.addItem(model)
            
    def _on_model_load_error(self, error_msg):
        """Handle model loading error"""
        self.progress.close()
        log_error(f"RevEng.AI | Failed to load models: {error_msg}")
        QMessageBox.critical(
            self,
            "RevEng.AI Model Loading Error",
            f"Failed to load available models: {error_msg}",
            QMessageBox.Ok
        )

    def upload_binary(self):
        """Start binary upload process"""
        # Validate model selection
        if not self.model_combo.currentText():
            log_warn("RevEng.AI | Model selection is required")
            QMessageBox.warning(
                self,
                "RevEng.AI Upload",
                "Please select a model for analysis.",
                QMessageBox.Ok
            )
            return
            
        # Create and show progress dialog
        self.progress = QProgressDialog("Uploading binary to RevEng.AI...", None, 0, 0, self)
        self.progress.setWindowTitle("RevEng.AI Upload")
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setCancelButton(None)
        self.progress.setMinimumWidth(400)
        self.progress.setMinimumHeight(100)
        self.progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                color: black;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
                background-color: #f0f0f0;
                min-width: 250px;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: #007bff;
                border-radius: 3px;
            }
            QLabel {
                color: black;
                font-size: 13px;
                padding: 10px;
            }
        """)
        
        # Create and start upload thread
        self.upload_thread = UploadBinaryThread(self.uploader, self.bv, self.get_upload_options())
        self.upload_thread.finished.connect(self._on_upload_finished)
        self.upload_thread.start()
        
        self.progress.show()
        
    def _on_upload_finished(self, success, error_message):
        """Handle upload completion"""
        self.progress.close()
        
        if success:
            QMessageBox.information(
                self,
                "RevEng.AI Upload",
                "Binary uploaded successfully!\nYou can now view the analysis on RevEng.AI",
                QMessageBox.Ok
            )
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed to upload binary: {error_message}")
            QMessageBox.critical(
                self,
                "RevEng.AI Upload Error",
                f"Failed to upload binary: {error_message}",
                QMessageBox.Ok
            )
        
    def browse_debug_info(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Debug Info or PDB",
            "",
            "Debug Info (*.pdb *.debug);;All Files (*.*)"
        )
        if file_path:
            self.debug_combo.setCurrentText(file_path)
            
    def get_upload_options(self):
        return {
            'debug_info': self.debug_combo.currentText(),
            'tags': [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()],
            'model': self.model_combo.currentText(),
            'is_private': self.private_radio.isChecked()
        } 