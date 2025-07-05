from binaryninja import log_info, log_error
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QSlider, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon
from revengai_bn.utils import create_progress_dialog
from revengai_bn.utils.data_thread import DataThread

class ResultTab(QWidget):

    def __init__(self, match_functions, bv, status_label):
        super().__init__()
        self.match_functions = match_functions
        self.bv = bv
        self.status_label = status_label
        self.columns = [
            "Successful", "Original Function Name", "Matched Function Name", 
            "Signature", "Matched Binary", "Similarity", "Confidence", "Error"
        ]
        self.current_matches = []
        self.selected_results = []
        self.match_thread = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._build_result_section()

    def _build_result_section(self):
        layout = QVBoxLayout()      

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels(self.columns)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Stretch)

        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.MultiSelection)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
        #self.results_table.itemSelectionChanged.connect(self.on_result_selection_changed)
        
        layout.addWidget(self.results_table)

        self.layout.addLayout(layout)
    
    def populate_results_table(self):
        """Populate the results table with function matches"""
        # Clear previous selections
        self.selected_results.clear()
        
        self.results_table.setRowCount(len(self.current_matches))
        
        for row, match in enumerate(self.current_matches):
            icon_path = match.get("icon_path", "")
            icon_text = match.get("icon_text", "")
            icon_item = QTableWidgetItem()
            icon_item.setIcon(QIcon(icon_path))
            icon_item.setText(icon_text)
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemIsEditable)
            icon_item.setData(Qt.UserRole, match)
            self.results_table.setItem(row, 0, icon_item)

            column_data = [
                "original_name",
                "matched_name",
                "signature",
                "matched_binary",
                "similarity",
                "confidence",
                "error"
            ]
            
            # Create and set items for each column
            for column, field in enumerate(column_data, start=1):
                item = QTableWidgetItem(match.get(field, "N/A"))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, match)
                self.results_table.setItem(row, column, item)
            
            # Auto-select successful results
            if icon_text == "Success":
                self.selected_results.append(match)
                # Select the entire row
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    if item:
                        item.setSelected(True)

        # Connect cell click signal to handler
        self.results_table.cellClicked.connect(self._handle_result_click)
        
        
    def on_checkbox_changed(self, item_or_row, column=None):
        if isinstance(item_or_row, QTableWidgetItem):  # Called from itemChanged
            row = item_or_row.row()
            is_checkbox = item_or_row.column() == 0
        else:  # Called from cellClicked
            row = item_or_row
            is_checkbox = column == 0

            result = self.results_table.item(row, 1).data(Qt.UserRole)
            result_id = str(result.get("id", "")) if result else None
            
            if result and result_id:
                is_checked = item_or_row.checkState() == Qt.Checked
                is_selected = result_id in [str(r.get("id", "")) for r in self.selected_results]
                
                if is_checked and not is_selected:
                    # Add to selection
                    self.selected_results.append(result)
                    # Select the row
                    for col in range(self.results_table.columnCount()):
                        row_item = self.results_table.item(row, col)
                        if row_item:
                            row_item.setSelected(True)
                    log_info(f"RevEng.AI | Added result to selection: {result.get('original_name', '')}")
                    
                elif not is_checked and is_selected:
                    # Remove from selection
                    self.selected_results = [r for r in self.selected_results if str(r.get("id", "")) != result_id]
                    # Deselect the row
                    for col in range(self.results_table.columnCount()):
                        row_item = self.results_table.item(row, col)
                        if row_item:
                            row_item.setSelected(False)
                    log_info(f"RevEng.AI | Removed result from selection: {result.get('original_name', '')}")
                
                # Update status
                self.status_label.setText(f"Selected {len(self.selected_results)} result(s)")
                log_info(f"RevEng.AI | Total selected results: {len(self.selected_results)}")

    def _handle_result_click(self, row, column):
        """Handle result click event"""
        result = self.results_table.item(row,1).data(Qt.UserRole)
        if result:
            # Check if already selected by comparing the actual result objects
            # Use original_name as identifier since it should be unique per function
            original_name = result.get('original_name', '')
            is_selected = any(r.get('original_name', '') == original_name for r in self.selected_results)
            
            if is_selected:
                # Remove from selection
                self.selected_results = [r for r in self.selected_results 
                                       if r.get('original_name', '') != original_name]
                # Deselect the row
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    if item:
                        item.setSelected(False)
                log_info(f"RevEng.AI | Removed result from selection: {original_name}")
            else:
                # Add to selection
                self.selected_results.append(result)
                # Select the row
                for col in range(self.results_table.columnCount()):
                    item = self.results_table.item(row, col)
                    if item:
                        item.setSelected(True)
                log_info(f"RevEng.AI | Added result to selection: {original_name}")
            
            log_info(f"RevEng.AI | Total selected results: {len(self.selected_results)}")
            
            # Update rename button state
            self.rename_selected_button.setEnabled(len(self.selected_results) > 0)
