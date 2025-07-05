from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QRadioButton, QButtonGroup,
                              QLineEdit, QGroupBox, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QCoreApplication
from binaryninja import log_info, log_error, log_warn
from .model_load_thread import ModelLoadThread
from .upload_thread import UploadBinaryThread
from revengai.utils import create_progress_dialog

class UploadDialog(QDialog):
    def __init__(self, config, uploader, bv):
        super().__init__()
        self.config = config
        self.uploader = uploader
        self.bv = bv
        self.model_thread = None
        self.upload_thread = None
        self.progress = None
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
        
        self.show()
        QCoreApplication.processEvents()
        
        self.load_models()


    def load_models(self):
        self.progress = create_progress_dialog(self, "RevEng.AI", "Loading available models...")
        
        self.model_thread = ModelLoadThread(self.uploader, self.bv)
        self.model_thread.finished.connect(self._on_models_loaded)
        self.model_thread.error.connect(self._on_model_load_error)
        self.model_thread.start()

        self.progress.show()
        QCoreApplication.processEvents()
        
    def _on_models_loaded(self, models):
        self.progress.close()
        self.model_combo.clear()
        for model in models:
            self.model_combo.addItem(model)
            
    def _on_model_load_error(self, error_msg):
        self.progress.close()
        log_error(f"RevEng.AI | Failed to load models: {error_msg}")
        QMessageBox.critical(
            self,
            "RevEng.AI Model Loading Error",
            f"Failed to load available models: {error_msg}",
            QMessageBox.Ok
        )
        self.reject()  

    def upload_binary(self):
        if not self.model_combo.currentText():
            log_warn("RevEng.AI | Model selection is required")
            QMessageBox.warning(
                self,
                "RevEng.AI Upload",
                "Please select a model for analysis.",
                QMessageBox.Ok
            )
            return
            
        self.progress = create_progress_dialog(self, "RevEng.AI Upload", "Uploading binary to RevEng.AI...")
        
        self.upload_thread = UploadBinaryThread(self.uploader, self.bv, self.get_upload_options())
        self.upload_thread.finished.connect(self._on_upload_finished)
        self.upload_thread.start()
        
        self.progress.show()
        QCoreApplication.processEvents()
        
    def _on_upload_finished(self, success, error_message):
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