from binaryninja import log_info, log_error
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGroupBox, QSlider, QCheckBox, QMessageBox)
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QIcon
from revengai.utils import create_progress_dialog
from revengai.utils.data_thread import DataThread

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
                self.results_table.setItem(row, column, item)
            
            # Auto-select successful results
            if icon_text == "Success":
                self.selected_results.append(match)

    def update_current_matches_with_signatures(self, selected_results):
        for match in self.current_matches:
            if match.get("nearest_neighbor_id", False):
                continue
            for result in selected_results:
                if match["nearest_neighbor_id"] == result["nearest_neighbor_id"]:
                    match["signature"] = result["signature"]
                    break
        self.populate_results_table()