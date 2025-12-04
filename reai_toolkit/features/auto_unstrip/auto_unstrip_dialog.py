import os
from binaryninja import log_error, log_info
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QCoreApplication
from reai_toolkit.utils import create_progress_dialog, DataThread, create_cancellable_progress_dialog
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QMessageBox, QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem

class AutoUnstripDialog(QDialog):
    def __init__(self, config, auto_unstrip, bv):
        super().__init__()
        self.config = config
        self.auto_unstrip = auto_unstrip
        self.selected_results = []
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
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        layout.addWidget(self.results_table)

        layout.addSpacing(20)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Rename Functions")
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
        self.save_button.clicked.connect(self._rename)
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
        self.show()
        QCoreApplication.processEvents()
        self._auto_unstrip()


    def _rename(self):
        self.progress = create_progress_dialog(self, "RevEng.AI Auto Unstrip", "Renaming selected functions...")
        self.progress.show()
        QCoreApplication.processEvents()  
    
        self.rename_thread = DataThread(self.auto_unstrip.rename_functions, self.bv, self.selected_results)
        self.rename_thread.finished.connect(self._on_rename_finished)
        self.rename_thread.start()


    def _on_rename_finished(self, success, message):
        self.progress.close()
        
        if success:
            QMessageBox.information(self, "RevEng.AI Auto Unstrip", message, QMessageBox.Ok)
            self.accept()
        else:
            log_error(f"RevEng.AI | Failed to rename functions: {message}")
            QMessageBox.critical(self, "RevEng.AI Auto Unstrip", f"Failed to rename functions: {message}", QMessageBox.Ok)
            self.reject()



    def _auto_unstrip(self):
        self.progress = create_cancellable_progress_dialog(self, "RevEng.AI Auto Unstrip", "Auto Unstripping binary...", self.auto_unstrip.cancel)
        self.progress.show()
        QCoreApplication.processEvents()  
        
        self.auto_unstrip_thread = DataThread(self.auto_unstrip.auto_unstrip, self.bv, callback_cancelled_reset = self.auto_unstrip.clear_cancelled)
        self.auto_unstrip_thread.finished.connect(self._on_auto_unstrip_finished)
        self.auto_unstrip_thread.start()

    def _on_auto_unstrip_finished(self, success, data):
        self.progress.close()
        
        if success:
            self.populate_results_table(data)
            message = f"Total functions found: {len(data)}"
        else:
            message = data
            log_error(f"RevEng.AI | Failed to auto unstrip binary: {message}")
            QMessageBox.critical(self, "RevEng.AI Auto Unstrip Error", f"Failed to auto unstrip binary: {message}", QMessageBox.Ok)
            self.reject()

    def populate_results_table(self, results):
        self.results_table.setRowCount(len(results))
        for i, result in enumerate(results):
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            select_item.setCheckState(Qt.Checked)
            self.results_table.setItem(i, 0, select_item)
            
            columns = [
                (1, "virtual_address", lambda x: f"0x{x:x}" if isinstance(x, int) else str(x)),
                (2, "current_name", lambda x: str(x)),
                (3, "suggested_name", lambda x: str(x)),
            ]

            for col_idx, field, transform in columns:
                value = result.get(field, "")
                try:
                    safe_value = transform(value)
                except Exception:
                    safe_value = str(value)
                item = QTableWidgetItem(safe_value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, result)
                log_info(f"RevEng.AI | row: {i}, column: {col_idx}, item: {item.data(Qt.UserRole)}")
                item.setSelected(False)
                self.results_table.setItem(i, col_idx, item)


            self.results_table.cellClicked.connect(self.on_checkbox_changed)
            try:
                self.results_table.cellClicked.disconnect()
            except:
                pass  
            self.results_table.cellClicked.connect(self.on_checkbox_changed)

            self.selected_results.append(result)

    def on_checkbox_changed(self, item_or_row, column=None):
        if isinstance(item_or_row, QTableWidgetItem):  # Called from itemChanged
            row = item_or_row.row()
            is_checkbox = item_or_row.column() == 0
        else:  # Called from cellClicked
            row = item_or_row
            is_checkbox = column == 0

        log_info(f"RevEng.AI | on_checkbox_changed called for row: {row}, column: {column}, is_checkbox: {is_checkbox}")

        result = self.results_table.item(row, 1).data(Qt.UserRole)
        log_info(f"RevEng.AI | result: {result}")
        result_virtual_address = result.get("virtual_address") if result else None
        log_info(f"RevEng.AI | result_virtual_address: {result_virtual_address}")
            
        if result and result_virtual_address is not None:
            log_info(f"RevEng.AI | result_virtual_address: {result_virtual_address}")
            is_selected = any(r.get("virtual_address") == result_virtual_address for r in self.selected_results)
            log_info(f"RevEng.AI | is_selected: {is_selected}")

            checkbox_item = self.results_table.item(row, 0)
            current_state = checkbox_item.checkState()
            
            # Clear row selection
            for col in range(self.results_table.columnCount()):
                row_item = self.results_table.item(row, col)
                if row_item:
                    row_item.setSelected(False)
            
            if current_state == Qt.Unchecked:
                log_info(f"RevEng.AI | Removing result from selection: {result_virtual_address}")
                self.selected_results = [r for r in self.selected_results if r.get("virtual_address") != result_virtual_address]
            else:
                log_info(f"RevEng.AI | Adding result to selection: {result_virtual_address}")
                if not is_selected:
                    self.selected_results.append(result)

                
            log_info(f"RevEng.AI | Total selected results: {len(self.selected_results)}")
