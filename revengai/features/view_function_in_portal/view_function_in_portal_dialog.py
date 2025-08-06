from PySide6.QtCore import Qt
from binaryninja import log_error
from revengai.utils import DataThread
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QMessageBox


class ViewFunctionInPortalDialog(QDialog):
    def __init__(self, config, view_function_in_portal, bv, func):
        super().__init__()
        self.config = config
        self.view_function_in_portal = view_function_in_portal
        self.bv = bv
        self.func = func
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: View Function in Portal")
        self.setWindowModality(Qt.WindowModal)
        self.setMinimumSize(400, 100)
        self.resize(400, 100)
        
        layout = QVBoxLayout()
        
        title_label = QLabel("Searching...")
        title_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(title_label)

        progress_bar = QProgressBar()
        progress_bar.setMinimumWidth(250)
        progress_bar.setMinimumHeight(20)
        layout.addWidget(progress_bar)
        
        self.setLayout(layout)
        
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

        options = {
            "function": self.func
        }

        self.view_function_in_portal_thread = DataThread(self.view_function_in_portal.view_function_in_portal, self.bv, options)
        self.view_function_in_portal_thread.finished.connect(self._on_view_function_in_portal_finished)
        self.view_function_in_portal_thread.start()

    def _on_view_function_in_portal_finished(self, success, message):
        if success:
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed: {message}")
            QMessageBox.critical(self, "RevEng.AI View Function in Portal Error", f"Failed to find function in portal: {message}", QMessageBox.Ok)
            self.reject()
