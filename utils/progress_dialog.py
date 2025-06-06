from PySide6.QtWidgets import QProgressDialog, QProgressBar
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