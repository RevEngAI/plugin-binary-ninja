from PySide6.QtWidgets import QProgressDialog, QProgressBar, QPushButton
from PySide6.QtCore import Qt

def create_progress_dialog(parent, title, message):
    progress = QProgressDialog(message, None, 0, 0, parent)
    progress.setWindowTitle(title)
    progress.setWindowModality(Qt.WindowModal)
    progress.setCancelButton(None)
    progress.setMinimumWidth(400)
    progress.setMinimumHeight(100)
    
    progress_bar = progress.findChild(QProgressBar)
    if progress_bar:
        progress_bar.setMinimumWidth(250)
        progress_bar.setMinimumHeight(20)
    
    progress.setStyleSheet("""
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
    
    return progress

def create_cancellable_progress_dialog(parent, title, message, cancel_callback=None):
    """Create a progress dialog with a cancel button that can stop threads"""
    progress = QProgressDialog(message, "Cancel", 0, 0, parent)
    progress.setWindowTitle(title)
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumWidth(400)
    progress.setMinimumHeight(100)
    
    # Style the cancel button
    cancel_button = progress.findChild(QPushButton)
    if cancel_button:
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
        """)
    
    progress_bar = progress.findChild(QProgressBar)
    if progress_bar:
        progress_bar.setMinimumWidth(250)
        progress_bar.setMinimumHeight(20)
    
    progress.setStyleSheet("""
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
    
    # Connect cancel callback if provided
    if cancel_callback:
        progress.canceled.connect(cancel_callback)
    
    return progress 