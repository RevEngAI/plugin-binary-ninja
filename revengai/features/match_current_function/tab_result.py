from binaryninja import log_info, log_error
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QSlider, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon
from revengai.utils import create_progress_dialog
from revengai.utils.data_thread import DataThread

class ResultTab(QWidget):

    def __init__(self, match_current_function, bv, status_label):
        super().__init__()
        self.match_current_function = match_current_function
        self.bv = bv
        self.status_label = status_label
        self.current_matches = []
        self.selected_result = {}
        self.match_thread = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._build_result_section()

    def _build_result_section(self):
        layout = QVBoxLayout()      

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Selected", "Original Function Name", "Matched Function Name", "Signature", "Matched Binary", "Similarity"
        ])
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)
            
        layout.addWidget(self.results_table)

        self.layout.addLayout(layout)

    def on_checkbox_changed(self, item_or_row, column=None):
        """Handle checkbox changes to ensure only one is selected at a time"""
        if isinstance(item_or_row, QTableWidgetItem):  # Called from itemChanged
            row = item_or_row.row()
            is_checkbox = item_or_row.column() == 0
        else:  # Called from cellClicked
            row = item_or_row
            is_checkbox = column == 0

        # Get the match data for this row
        if row < len(self.current_matches):
            match = self.current_matches[row]
        else:
            return
            
        if match:
            checkbox_item = self.results_table.item(row, 0)
            current_state = checkbox_item.checkState()
            
            # Toggle state if clicked on non-checkbox cell
            if is_checkbox:
                new_state = current_state
            else:
                new_state = Qt.Unchecked if current_state == Qt.Checked else Qt.Checked
                checkbox_item.setCheckState(new_state)
            
            # Handle unique selection (only one can be checked)
            if new_state == Qt.Checked:
                # Uncheck all other checkboxes
                for i in range(self.results_table.rowCount()):
                    if i != row:
                        other_checkbox = self.results_table.item(i, 0)
                        if other_checkbox and other_checkbox.checkState() == Qt.Checked:
                            other_checkbox.setCheckState(Qt.Unchecked)
                
                # Update selected result with the current match
                self.selected_result = match
                log_info(f"RevEng.AI | Selected function match: {match.get('matched_name', 'Unknown')}")
            else:
                # If unchecked, clear selection
                self.selected_result = {}
                log_info(f"RevEng.AI | Deselected function match")
    
    def populate_results_table(self):
        """Populate the results table with function matches"""
        self.selected_result = {}
        self.results_table.setRowCount(0)
        self.results_table.setRowCount(len(self.current_matches))
        
        # Safely disconnect existing connections
        try:
            self.results_table.itemChanged.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        
        for row, match in enumerate(self.current_matches):
            select_item = QTableWidgetItem()
            select_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            select_item.setCheckState(Qt.Unchecked)
            self.results_table.setItem(row, 0, select_item)

            column_data = [
                "original_name",
                "matched_name",
                "signature",
                "matched_binary",
                "similarity",
            ]
            
            # Create and set items for each column
            for column, field in enumerate(column_data, start=1):
                item = QTableWidgetItem(match.get(field, "N/A"))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setData(Qt.UserRole, match)
                item.setSelected(False)
                self.results_table.setItem(row, column, item)

        # Connect signals after populating
        self.results_table.itemChanged.connect(self.on_checkbox_changed)
        
        # Safely disconnect and reconnect cellClicked
        try:
            self.results_table.cellClicked.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        
        self.results_table.cellClicked.connect(self.on_checkbox_changed)

    def update_current_matches_with_signatures(self, signatures):
        for match in self.current_matches:
            if not match.get("nearest_neighbor_id"):
                continue
            for signature_data in signatures:
                if match["nearest_neighbor_id"] == signature_data["nearest_neighbor_id"]:
                    match["signature"] = signature_data["signature"]
                    break
        self.populate_results_table()