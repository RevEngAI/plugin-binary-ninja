from binaryninja import log_info, log_error, log_debug
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit, 
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QCoreApplication
from reai_toolkit.utils.ui.progress import create_progress_dialog
from reai_toolkit.utils.core.threading import DataThread
800
class CollectionsPopup(QDialog):
    def __init__(self, match_functions, bv, status_label=None, parent=None, write_selected_collections=None):
        super().__init__(parent)
        self.setWindowTitle("RevEng.AI: Search Collections")
        self.setMinimumSize(600, 400)
        self.resize(1000, 750)
        self.match_functions = match_functions
        self.bv = bv
        self.status_label = status_label or QLabel("Ready!")
        self.current_collections = []
        self.selected_collections = []
        self.search_collections_thread = None
        self.write_selected_collections = write_selected_collections
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
        self.search_input.returnPressed.connect(self._search_collections)

        description_label = QLabel(
            "Search (e.g. sha_256_hash:{}, tag:{}, collection_name:{}, function_name:{}, model_name:{})"
        )
        description_label.setWordWrap(True)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self._search_collections)
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

        self.collections_table = QTableWidget()
        self.collections_table.setColumnCount(6)
        self.collections_table.setHorizontalHeaderLabels([" ", "Name", "ID", "Scope", "Owner", "Date"])
        self.collections_table.setMinimumHeight(180)
        self.collections_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        header = self.collections_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.collections_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.collections_table.setSelectionMode(QTableWidget.MultiSelection)
        self.collections_table.setAlternatingRowColors(True)
        self.collections_table.verticalHeader().setVisible(False)
        
        search_layout.addWidget(self.collections_table)
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

    def _search_collections(self):
        self.progress = create_progress_dialog(self, "RevEng.AI Search Collections", "Searching collections...")
        self.progress.show()
        QCoreApplication.processEvents() 

        search_term = self.search_input.text().strip()
        log_info(f"RevEng.AI | Search term: {search_term}")

        options = {
            "item_type": "Collection",
            "search_term": search_term
        }

        self.search_collections_thread = DataThread(self.match_functions.search_items, self.bv, options)
        self.search_collections_thread.finished.connect(self._on_search_collections_finished)
        self.search_collections_thread.start()

    def _on_search_collections_finished(self, success, data):
        self.progress.close()
        if success:
            self.selected_collections.clear()
            self.collections_table.clearSelection()
            self.collections_table.setRowCount(0)
            
            self.current_collections = data
            message = f"Found {len(self.current_collections)} collections!"
            log_info(f"RevEng.AI | {message}")
            self.status_label.setText(message)
            self.populate_collections_table()
            
        else:
            message = f"Error searching collections: {data}"
            log_error(f"RevEng.AI | {message}")
            self.status_label.setText(message)
            QMessageBox.critical(self, "Search Error", message)
                    
    def populate_collections_table(self):
        self.collections_table.setRowCount(len(self.current_collections))
        try:
            self.collections_table.itemChanged.disconnect()
        except Exception:
            pass
        
        for row, collection in enumerate(self.current_collections):
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            select_item.setCheckState(Qt.Unchecked)
            self.collections_table.setItem(row, 0, select_item)
            
            columns = [
                (1, "name", lambda x: x),
                (2, "id", lambda x: x),
                (3, "scope", lambda x: x),
                (4, "owner", lambda x: x),
                (5, "date", lambda x: x)
            ]

            for col_idx, field, transform in columns:
                value = transform(collection.get(field, ""))
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, collection)
                item.setSelected(False)
                item.setToolTip(value)
                self.collections_table.setItem(row, col_idx, item)

        self.collections_table.itemChanged.connect(self.on_checkbox_changed)
        try:
            self.collections_table.cellClicked.disconnect()
        except Exception:
            pass  
        self.collections_table.cellClicked.connect(self.on_checkbox_changed)

    def on_checkbox_changed(self, item_or_row, column=None):
        if isinstance(item_or_row, QTableWidgetItem): 
            row = item_or_row.row()
            is_checkbox = item_or_row.column() == 0
        else:
            row = item_or_row
            is_checkbox = column == 0 if column is not None else False

        collection = self.collections_table.item(row, 1).data(Qt.UserRole)
        collection_id = str(collection.get("id", "")) if collection else None
            
        if collection and collection_id:
            checkbox_item = self.collections_table.item(row, 0)
            current_state = checkbox_item.checkState()
            
            if is_checkbox:
                new_state = current_state
            else:
                new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
                checkbox_item.setCheckState(new_state)

            is_selected = collection_id in [str(c.get("id", "")) for c in self.selected_collections]
            
            if new_state == Qt.Checked and not is_selected:
                self.selected_collections.append(collection)
                for col in range(self.collections_table.columnCount()):
                    row_item = self.collections_table.item(row, col)
                    if row_item:
                        row_item.setSelected(True)
                log_info(f"RevEng.AI | Added collection to selection: {collection.get('name', '')}")
                    
            elif new_state == Qt.Unchecked and is_selected:
                self.selected_collections = [c for c in self.selected_collections if str(c.get("id", "")) != collection_id]
                for col in range(self.collections_table.columnCount()):
                    row_item = self.collections_table.item(row, col)
                    if row_item:
                        row_item.setSelected(False)
                log_info(f"RevEng.AI | Removed collection from selection: {collection.get('name', '')}")
                
            self.status_label.setText(f"Selected {len(self.selected_collections)} collection(s)")
            final_string = ""
            for collection in self.selected_collections:
                final_string += f"{collection.get('id', '')},"
            final_string = final_string[:-1] if final_string else ""
            self.write_selected_collections(final_string)
            log_info(f"RevEng.AI | Total selected collections: {len(self.selected_collections)}")

