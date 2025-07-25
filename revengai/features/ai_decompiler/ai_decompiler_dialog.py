from binaryninja import log_error
from PySide6.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QCheckBox, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QProgressBar
from revengai.utils import create_progress_dialog
from revengai.utils.data_thread import DataThread
import os

class AIDecompilerDialog(QDockWidget):
    def __init__(self, config, ai_decompiler, bv, func):
        super().__init__()
        self.config = config
        self.ai_decompiler = ai_decompiler
        self.bv = bv
        self.func = func
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: AI Decompiler")
        
        # Create a widget to hold the layout
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        title_label = QLabel("Getting AI decompiler...")
        title_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(title_label)

        progress_bar = QProgressBar()
        progress_bar.setMinimumWidth(250)
        progress_bar.setMinimumHeight(20)
        layout.addWidget(progress_bar)
        
        # Set the content widget
        self.setWidget(content_widget)
        
        self.setStyleSheet("""
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
        """)
