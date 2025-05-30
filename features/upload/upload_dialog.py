from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                              QComboBox, QPushButton, QRadioButton, QButtonGroup,
                              QLineEdit, QGroupBox, QFileDialog, QProgressDialog, QMessageBox)
from PySide6.QtCore import Qt
from binaryninja import log_info, log_error

class UploadDialog(QDialog):
    def __init__(self, config, uploader, bv):
        super().__init__()
        self.config = config
        self.uploader = uploader
        self.bv = bv
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
        for model in self.uploader.get_models():
            self.model_combo.addItem(model)
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


    def upload_binary(self):
        try:
            progress = QProgressDialog("Uploading binary to RevEng.AI...", None, 0, 0)
            progress.setWindowTitle("RevEng.AI Upload")
            progress.setWindowModality(Qt.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumWidth(400)
            progress.setMinimumHeight(100)
            progress.setStyleSheet("""
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

            progress.show()

            upload_try = self.uploader.upload_binary(self.bv, self.get_upload_options())
            
            progress.close()

            if not upload_try:
                raise Exception("Failed to upload binary")

            QMessageBox.information(
                None,
                "RevEng.AI Upload",
                "Binary uploaded successfully!\nYou can now view the analysis on RevEng.AI",
                QMessageBox.Ok
            )
            self.accept()
            
        except Exception as e:
            log_error(f"Failed to upload binary: {str(e)}")
            QMessageBox.critical(
                None,
                "RevEng.AI Upload Error",
                f"Failed to upload binary: {str(e)}",
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