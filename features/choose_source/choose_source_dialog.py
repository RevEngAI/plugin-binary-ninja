from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton, QHBoxLayout
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QCoreApplication
from .analysis_load_thread import AnalysisLoadThread
from .choose_source_thread import ChooseSourceThread
from binaryninja import log_error
from PySide6.QtWidgets import QMessageBox
from revengai_bn.utils import create_progress_dialog
import os

class ChooseSourceDialog(QDialog):
    def __init__(self, config, choose_source, bv):
        super().__init__()
        self.config = config
        self.choose_source = choose_source
        self.bv = bv
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Choose Source")
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
        title_label = QLabel("Select Analysis Source")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        description_label = QLabel(
            "Choose the source for your binary analysis. This selection will be used for all subsequent "
            "features in the plugin, including auto-unstripping, function analysis, and other operations.\n\n"
            #"The selected source will determine which database and models are used for your analysis tasks."
        )
        description_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        info_layout.addWidget(description_label)
        header_layout.addLayout(info_layout, stretch=1)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        self.combo = QComboBox()
        layout.addWidget(self.combo)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.setStyleSheet("""
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
        self.ok_button.clicked.connect(self._choose_source)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.show()
        QCoreApplication.processEvents()
        
        self.load_analysis()

    def load_analysis(self):
        self.progress = create_progress_dialog(self, "RevEng.AI", "Loading analysis...")
        self.progress.show()
        QCoreApplication.processEvents()

        self.analysis_thread = AnalysisLoadThread(self.choose_source, self.bv)
        self.analysis_thread.finished.connect(self._on_analysis_loaded)
        self.analysis_thread.error.connect(self._on_analysis_load_error)
        self.analysis_thread.start()
        

    def _on_analysis_loaded(self, analysis):
        self.progress.close()
        self.combo.clear()
        for analysis in analysis:
            self.combo.addItem(analysis)

    def _on_analysis_load_error(self, error_msg):
        self.progress.close()
        log_error(f"RevEng.AI | Failed to load analysis: {error_msg}")
        QMessageBox.critical(
            self,
            "RevEng.AI Analysis Loading Error",
            f"Failed to load available analysis: {error_msg}",
            QMessageBox.Ok
        )
        self.reject()   

    def _choose_source(self):
        if not self.combo.currentText():
            log_warn("RevEng.AI | Source selection is required")
            QMessageBox.warning(
                self,
                "RevEng.AI Choose Source",
                "Please select a source for analysis.",
                QMessageBox.Ok
            )
            return
            
        self.progress = create_progress_dialog(self, "RevEng.AI Choose Source", "Choosing source...")
        
        self.choose_source_thread = ChooseSourceThread(self.choose_source, self.bv, self.combo.currentText())
        self.choose_source_thread.finished.connect(self._on_choose_source_finished)
        self.choose_source_thread.start()
        
        self.progress.show()
        QCoreApplication.processEvents()
        
    def _on_choose_source_finished(self, success, error_message):
        self.progress.close()
        
        if success:
            QMessageBox.information(
                self,
                "RevEng.AI Choose Source",
                "Source chosen successfully!\nYou can now view the analysis on RevEng.AI",
                QMessageBox.Ok
            )
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed to choose source: {error_message}")
            QMessageBox.critical(
                self,
                "RevEng.AI Choose Source Error",
                f"Failed to choose source: {error_message}",
                QMessageBox.Ok
            )