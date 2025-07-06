from binaryninja import BinaryView, PluginCommand, log_info, log_error
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, 
                             QGroupBox, QRadioButton, QSpacerItem,
                             QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QMessageBox
from revengai.utils import create_progress_dialog
from .auto_unstrip_thread import AutoUnstripThread
import os

class AutoUnstripDialog(QDialog):
    def __init__(self, config, auto_unstrip, bv):
        super().__init__()
        self.config = config
        self.auto_unstrip = auto_unstrip
        self.bv = bv
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Auto Unstrip Binary")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        
        logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "images", "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_label.setPixmap(pixmap)
        header_layout.addWidget(logo_label)
        
        info_layout = QVBoxLayout()
        title_label = QLabel("Auto Unstrip Binary")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        description_label = QLabel(
            "Using official RevEng.AI sources, function names will be recovered based on a high similarity and confidence threshold and limited to available debug symbols.\nFunctions will be renamed automatically for easier analysis.\n\nThis process may take several minutes depending on the binary size."
        )
        description_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        info_layout.addWidget(description_label)
        header_layout.addLayout(info_layout, stretch=1)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Auto Unstrip")
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
        self.save_button.clicked.connect(self._auto_unstrip)
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

    def _auto_unstrip(self):
        log_info("RevEng.AI | Auto Unstripping binary")
        # Create and show progress dialog using utility function
        self.progress = create_progress_dialog(self, "RevEng.AI Auto Unstrip", "Auto Unstripping binary...")
        
        # Create and start upload thread
        self.auto_unstrip_thread = AutoUnstripThread(self.auto_unstrip, self.bv)
        self.auto_unstrip_thread.finished.connect(self._on_auto_unstrip_finished)
        self.auto_unstrip_thread.start()
        
        self.progress.show()
        QCoreApplication.processEvents()    
        

    def _on_auto_unstrip_finished(self, success, message):
        """Handle auto unstrip completion"""
        self.progress.close()
        
        if success:
            QMessageBox.information(
                self,
                "RevEng.AI Auto Unstrip",
                f"Binary auto unstripped successfully!\n{message}",
                QMessageBox.Ok
            )
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed to auto unstrip binary: {message}")
            QMessageBox.critical(
                self,
                "RevEng.AI Auto Unstrip Error",
                f"Failed to auto unstrip binary: {message}",
                QMessageBox.Ok
            ) 
