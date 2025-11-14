from binaryninja import log_info, log_error, log_debug
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, 
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QCoreApplication
from reai_toolkit.utils.ui.progress import create_progress_dialog
from reai_toolkit.utils.core.threading import DataThread
800
class BinariesPopup(QDialog):
    def __init__(self, match_functions, bv, status_label=None, parent=None, write_selected_binaries=None):
        super().__init__(parent)
        self.setWindowTitle("RevEng.AI: Search Binaries")
        self.setMinimumSize(600, 400)
        self.resize(1000, 750)
        self.match_functions = match_functions
        self.bv = bv
        self.status_label = status_label or QLabel("Ready!")
        self.current_binaries = []
        self.selected_binaries = []
        self.search_binaries_thread = None
        self.write_selected_binaries = write_selected_binaries
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        self._build_search_section(main_layout)
        self._build_status_and_buttons(main_layout)

    def _build_search_section(self, parent_layout):
        search_group = QGroupBox()
        search_layout = QVBoxLayout()
    
        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        self.search_input.returnPressed.connect(self._search_binaries)

        description_label = QLabel(
            "Search (e.g. sha_256_hash:{}, tag:{}, binary_name:{}, function_name:{}, model_name:{})"
        )
        description_label.setWordWrap(True)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._search_binaries)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 4px 10px;
                border-radius: 4px;  
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_button)
    
        search_layout.addLayout(search_input_layout)
        search_layout.addWidget(description_label)

        self.binaries_table = QTableWidget()
        self.binaries_table.setColumnCount(5)
        self.binaries_table.setHorizontalHeaderLabels([" ", "Name", "Binary ID", "SHA-256 Hash", "Date"])
        self.binaries_table.setMinimumHeight(180)
        self.binaries_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = self.binaries_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.binaries_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.binaries_table.setSelectionMode(QTableWidget.MultiSelection)
        self.binaries_table.setAlternatingRowColors(True)
        self.binaries_table.verticalHeader().setVisible(False)
        
        search_layout.addWidget(self.binaries_table)
        search_group.setLayout(search_layout)
        parent_layout.addWidget(search_group)

    def _build_status_and_buttons(self, parent_layout):
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        # Add OK and Cancel buttons for the popup
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        status_layout.addWidget(self.ok_button)
        status_layout.addWidget(self.cancel_button)
        parent_layout.addLayout(status_layout)

    def _search_binaries(self):
        self.progress = create_progress_dialog(self, "RevEng.AI Search Binaries", "Searching binaries...")
        self.progress.show()
        QCoreApplication.processEvents() 

        search_term = self.search_input.text().strip()
        log_info(f"RevEng.AI | Search term: {search_term}")

        options = {
            "item_type": "Binary",
            "search_term": search_term
        }

        self.search_binaries_thread = DataThread(self.match_functions.search_items, self.bv, options)
        self.search_binaries_thread.finished.connect(self._on_search_binaries_finished)
        self.search_binaries_thread.start()

    def _on_search_binaries_finished(self, success, data):
        self.progress.close()
        if success:
            self.selected_binaries.clear()
            self.binaries_table.clearSelection()
            self.binaries_table.setRowCount(0)
            
            self.current_binaries = data
            message = f"Found {len(self.current_binaries)} binaries!"
            log_info(f"RevEng.AI | {message}")
            self.status_label.setText(message)
            self.populate_binaries_table()
            
        else:
            message = f"Error searching binaries: {data}"
            log_error(f"RevEng.AI | {message}")
            self.status_label.setText(message)
            QMessageBox.critical(self, "Search Error", message)
                    
    def populate_binaries_table(self):
        self.binaries_table.setRowCount(len(self.current_binaries))
        try:
            self.binaries_table.itemChanged.disconnect()
        except Exception:
            pass
        
        for row, binary in enumerate(self.current_binaries):
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            select_item.setCheckState(Qt.Unchecked)
            self.binaries_table.setItem(row, 0, select_item)
            
            columns = [
                (1, "name", lambda x: x),
                (2, "binary_id", lambda x: x),
                (3, "sha_256_hash", lambda x: x),
                (4, "date", lambda x: x)
            ]

            for col_idx, field, transform in columns:
                value = transform(binary.get(field, ""))
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, binary)
                item.setSelected(False)
                item.setToolTip(value)
                self.binaries_table.setItem(row, col_idx, item)

        self.binaries_table.itemChanged.connect(self.on_checkbox_changed)
        try:
            self.binaries_table.cellClicked.disconnect()
        except Exception:
            pass  
        self.binaries_table.cellClicked.connect(self.on_checkbox_changed)

    def on_checkbox_changed(self, item_or_row, column=None):
        if isinstance(item_or_row, QTableWidgetItem): 
            row = item_or_row.row()
            is_checkbox = item_or_row.column() == 0
        else:
            row = item_or_row
            is_checkbox = column == 0 if column is not None else False

        binary = self.binaries_table.item(row, 1).data(Qt.UserRole)
        binary_id = str(binary.get("binary_id", "")) if binary else None
            
        if binary and binary_id:
            checkbox_item = self.binaries_table.item(row, 0)
            current_state = checkbox_item.checkState()
            
            if is_checkbox:
                new_state = current_state
            else:
                new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
                checkbox_item.setCheckState(new_state)

            is_selected = binary_id in [str(b.get("binary_id", "")) for b in self.selected_binaries]
            
            if new_state == Qt.Checked and not is_selected:
                self.selected_binaries.append(binary)
                for col in range(self.binaries_table.columnCount()):
                    row_item = self.binaries_table.item(row, col)
                    if row_item:
                        row_item.setSelected(True)
                log_info(f"RevEng.AI | Added binary to selection: {binary.get('name', '')}")
                    
            elif new_state == Qt.Unchecked and is_selected:
                self.selected_binaries = [b for b in self.selected_binaries if str(b.get("binary_id", "")) != binary_id]
                for col in range(self.binaries_table.columnCount()):
                    row_item = self.binaries_table.item(row, col)
                    if row_item:
                        row_item.setSelected(False)
                log_info(f"RevEng.AI | Removed binary from selection: {binary.get('name', '')}")
                
            self.status_label.setText(f"Selected {len(self.selected_binaries)} binary(s)")
            final_string = ""
            for binary in self.selected_binaries:
                final_string += f"{binary.get('binary_id', '')},"
            final_string = final_string[:-1] if final_string else ""
            self.write_selected_binaries(final_string)
            log_info(f"RevEng.AI | Total selected binaries: {len(self.selected_binaries)}")

