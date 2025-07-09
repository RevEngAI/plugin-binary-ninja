from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QAbstractItemView, QLineEdit, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from binaryninja import log_info

class ResultTab(QWidget):

    def __init__(self, match_functions, bv, status_label):
        super().__init__()
        self.match_functions = match_functions
        self.bv = bv
        self.status_label = status_label
        self.current_matches = []
        self.selected_results = []
        self.match_thread = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self._build_result_section()

    def _build_result_section(self):
        layout = QVBoxLayout()   

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search results")
        self.search_bar.textChanged.connect(self.filter_results)
        layout.addWidget(self.search_bar)

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Successful", "Original Function Name", "Matched Function Name", 
            "Signature", "Matched Binary", "Similarity", "Confidence", "Error"
        ])
        self.results_table.setSelectionMode(QAbstractItemView.NoSelection)
        
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

        self.status_label = QLabel("No results yet")
        layout.addWidget(self.status_label)

        self.layout.addLayout(layout)

    def filter_results(self, text):
        log_info(f"RevEng.AI | Filtering results: {text}")
        for row in range(self.results_table.rowCount()):
            self.results_table.setRowHidden(row, True)
            for col in range(self.results_table.columnCount()):
                item = self.results_table.item(row, col)
                if item:
                    if text.lower() in item.text().lower():
                        log_info(f"RevEng.AI | Filtering results: {item.text()}")
                        self.results_table.setRowHidden(row, False)
                        break

    def populate_results_table(self):
        self.selected_results.clear()
        
        self.results_table.setRowCount(0)
        self.results_table.setRowCount(len(self.current_matches))
        
        for row, match in enumerate(self.current_matches):
            icon_path = match.get("icon_path", "")
            icon_text = match.get("icon_text", "")
            icon_item = QTableWidgetItem()
            icon_item.setIcon(QIcon(icon_path))
            icon_item.setText(icon_text)
            icon_item.setFlags(icon_item.flags() & ~Qt.ItemIsEditable)
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

            for column, field in enumerate(column_data, start=1):
                value = match.get(field, "N/A")
                if field != "signature":
                    value = value if len(value) < 25 else value[:22] + "..."
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.results_table.setItem(row, column, item)
            
            if icon_text == "Success":
                self.selected_results.append(match)

    def update_current_matches_with_signatures(self, selected_results):
        log_info(f"RevEng.AI | Updating current matches with signatures")
        for match in self.current_matches:
            if not match.get("nearest_neighbor_id", False):
                continue
            for result in selected_results:
                if not result.get("nearest_neighbor_id", False):
                    continue
                if match["nearest_neighbor_id"] == result["nearest_neighbor_id"]:
                    log_info(f"RevEng.AI | Found signature for {match['original_name']}")
                    match["signature"] = result["signature"]
                    break
        self.populate_results_table()