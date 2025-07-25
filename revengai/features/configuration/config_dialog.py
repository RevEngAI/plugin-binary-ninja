from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QLineEdit, QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from binaryninja import log_info, log_error, log_warn
import os
from .config_save_thread import ConfigSaveThread
from revengai.utils import create_progress_dialog

class ConfigDialog(QDialog):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.save_thread = None
        self.progress = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Configuration Wizard")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "logo.png") ## review that line
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        else:
            log_info("RevEng.AI logo not found at: " + logo_path)
        header_layout.addWidget(logo_label)
        
        welcome_layout = QVBoxLayout()
        title_label = QLabel("Welcome to RevEng.AI!")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        description_label = QLabel(
            "To get started, you'll need to configure your API key and host URL.\n"
            "You can get your API key from your RevEng.AI account settings."
        )
        description_label.setWordWrap(True)
        welcome_layout.addWidget(title_label)
        welcome_layout.addWidget(description_label)
        header_layout.addLayout(welcome_layout, stretch=1)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)
        
        api_key_label = QLabel("API Key:")
        api_key_label.setStyleSheet("font-weight: bold;")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your RevEng.AI API key")
        self.api_key_input.setText(self.config.api_key if self.config.api_key else "")

        layout.addWidget(api_key_label)
        layout.addWidget(self.api_key_input)
        layout.addSpacing(10)
        
        host_label = QLabel("Host URL:")
        host_label.setStyleSheet("font-weight: bold;")
        self.host_input = QLineEdit()
        self.host_input.setPlaceholderText("Enter the RevEng.AI host URL")
        self.host_input.setText(self.config.host if self.config.host else "")

        layout.addWidget(host_label)
        layout.addWidget(self.host_input)
        layout.addSpacing(20)
        
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Configuration")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #4400ff;
            }
        """)
        self.save_button.clicked.connect(self.save_config)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def save_config(self):
        api_key = self.api_key_input.text().strip()
        host = self.host_input.text().strip()

        if not api_key:
            log_warn("RevEng.AI | API Key field is empty")
            QMessageBox.warning(
                self, 
                "RevEng.AI Configuration", 
                "API Key is required to use RevEng.AI services.",
                QMessageBox.Ok
            )
            return
            
        if not host:
            log_warn("RevEng.AI | Host URL field is empty")
            QMessageBox.warning(
                self, 
                "RevEng.AI Configuration", 
                "Host URL is required to connect to RevEng.AI services.",
                QMessageBox.Ok
            )
            return

        self.progress = create_progress_dialog(self, "RevEng.AI Configuration", "Testing API key...")
        
        self.save_thread = ConfigSaveThread(self.config, api_key, host)
        self.save_thread.finished.connect(self._on_save_finished)
        self.save_thread.start()
        
        self.progress.show()

    def _on_save_finished(self, success, error_message):
        self.progress.close()
        
        if success:
            log_info("RevEng.AI | Configuration saved successfully!")
            QMessageBox.information(
                self, 
                "RevEng.AI Configuration",
                "Configuration saved successfully!\nYou can now start using RevEng.AI services.",
                QMessageBox.Ok
            )
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed to save configuration: {error_message}")
            QMessageBox.critical(
                self, 
                "RevEng.AI Configuration Error",
                f"Failed to save configuration: {error_message}",
                QMessageBox.Ok
            ) 