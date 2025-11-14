import os
from binaryninja import log_error
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QCoreApplication
from reai_toolkit.utils import create_progress_dialog, DataThread
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QMessageBox, QTableWidget, QHeaderView, QAbstractItemView

class AutoUnstripDialog(QDialog):
    def __init__(self, config, auto_unstrip, bv):
        super().__init__()
        self.config = config
        self.auto_unstrip = auto_unstrip
        self.bv = bv
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Auto Unstrip Binary")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)


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
        description_label = QLabel("Automatically rename unknown functions.")
        description_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        info_layout.addWidget(description_label)
        header_layout.addLayout(info_layout, stretch=1)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Select", "Virtual Address", "Current Name", "Suggested Name", 
        ])
        self.results_table.setSelectionMode(QAbstractItemView.NoSelection)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        layout.addWidget(self.results_table)

        self.debug_symbols_checkbox = QCheckBox("Limit Matches to Debug Symbols")
        self.debug_symbols_checkbox.setChecked(True)
        layout.addWidget(self.debug_symbols_checkbox)
        self.data_types_checkbox = QCheckBox("Get functions Data Types (renaming may take longer)")
        self.data_types_checkbox.setChecked(False)
        layout.addWidget(self.data_types_checkbox)

        layout.addSpacing(20)

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
        self.progress = create_progress_dialog(self, "RevEng.AI Auto Unstrip", "Auto Unstripping binary...")
        self.progress.show()
        QCoreApplication.processEvents()  

        options = {
            "debug_symbols": self.debug_symbols_checkbox.isChecked(),
            "data_types": self.data_types_checkbox.isChecked()
        }
        
        self.auto_unstrip_thread = DataThread(self.auto_unstrip.auto_unstrip, self.bv, options)
        self.auto_unstrip_thread.finished.connect(self._on_auto_unstrip_finished)
        self.auto_unstrip_thread.start()

    def _on_auto_unstrip_finished(self, success, message):
        self.progress.close()
        
        if success:
            QMessageBox.information(self, "RevEng.AI Auto Unstrip", f"Binary auto unstripped successfully!\n{message}", QMessageBox.Ok)
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed to auto unstrip binary: {message}")
            QMessageBox.critical(self, "RevEng.AI Auto Unstrip Error", f"Failed to auto unstrip binary: {message}", QMessageBox.Ok)
            self.reject()
