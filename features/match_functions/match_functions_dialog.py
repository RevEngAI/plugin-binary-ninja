from binaryninja import BinaryView, log_info, log_error
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTabWidget, QWidget, QMessageBox,
                             QCheckBox, QDoubleSpinBox, QSpinBox, QGroupBox,
                             QSplitter, QTextEdit, QProgressBar)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon
from revengai_bn.utils import create_progress_dialog
from .match_functions_thread import MatchFunctionsThread
import os

class MatchFunctionsDialog(QDialog):
    def __init__(self, config, match_functions, bv):
        super().__init__()
        self.config = config
        self.match_functions = match_functions
        self.bv = bv
        self.current_matches = []
        self.current_collections = []
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Match Functions")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        # Main layout
        main_layout = QVBoxLayout()

        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Search tab
        search_tab = self.create_search_tab()
        self.tab_widget.addTab(search_tab, "Search")
        
        # Results tab
        results_tab = self.create_results_tab()
        self.tab_widget.addTab(results_tab, "Results")
        
        main_layout.addWidget(self.tab_widget)

        # Status bar
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def create_search_tab(self):
        """Create the search tab with collection search functionality"""
        search_widget = QWidget()
        layout = QVBoxLayout()

        # Search section
        search_group = QGroupBox("Search Collections")
        search_layout = QVBoxLayout()
        
        # Search input
        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term (e.g., 'stealc')")
        self.search_input.returnPressed.connect(self.search_collections)
        
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.search_collections)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.search_button)
        search_layout.addLayout(search_input_layout)

        # Collections table
        self.collections_table = QTableWidget()
        self.collections_table.setColumnCount(5)
        self.collections_table.setHorizontalHeaderLabels(["Name", "Type", "Date", "Model Name", "Owner"])
        
        header = self.collections_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        self.collections_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.collections_table.setAlternatingRowColors(True)
        
        search_layout.addWidget(self.collections_table)
        search_group.setLayout(search_layout)
        layout.addWidget(search_group)

        # Match settings section
        settings_group = QGroupBox("Match Settings")
        settings_layout = QVBoxLayout()
        
        # Distance threshold
        distance_layout = QHBoxLayout()
        distance_layout.addWidget(QLabel("Distance Threshold:"))
        self.distance_spinbox = QDoubleSpinBox()
        self.distance_spinbox.setRange(0.01, 1.0)
        self.distance_spinbox.setValue(0.1)
        self.distance_spinbox.setSingleStep(0.01)
        self.distance_spinbox.setDecimals(2)
        distance_layout.addWidget(self.distance_spinbox)
        distance_layout.addStretch()
        settings_layout.addLayout(distance_layout)
        
        # Max matches
        matches_layout = QHBoxLayout()
        matches_layout.addWidget(QLabel("Max Matches:"))
        self.max_matches_spinbox = QSpinBox()
        self.max_matches_spinbox.setRange(1, 100)
        self.max_matches_spinbox.setValue(10)
        matches_layout.addWidget(self.max_matches_spinbox)
        matches_layout.addStretch()
        settings_layout.addLayout(matches_layout)
        
        # Debug symbols checkbox
        self.debug_symbols_checkbox = QCheckBox("Limit Matches to Debug Symbols")
        self.debug_symbols_checkbox.setChecked(True)
        settings_layout.addWidget(self.debug_symbols_checkbox)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Action buttons
        button_layout = QHBoxLayout()
        
        self.match_button = QPushButton("Match Functions")
        self.match_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        self.match_button.clicked.connect(self.start_matching)
        
        button_layout.addWidget(self.match_button)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        search_widget.setLayout(layout)
        return search_widget

    def create_results_tab(self):
        """Create the results tab with function match results"""
        results_widget = QWidget()
        layout = QVBoxLayout()

        # Results header
        header_layout = QHBoxLayout()
        self.results_label = QLabel("Total Functions Analyzed: 0 | Successful Analyses: 0 | Skipped Analyses: 0")
        header_layout.addWidget(self.results_label)
        header_layout.addStretch()
        
        # Action buttons
        self.fetch_results_button = QPushButton("Fetch Results")
        self.fetch_data_types_button = QPushButton("Fetch Data Types")
        self.rename_selected_button = QPushButton("Rename Selected")
        
        for button in [self.fetch_results_button, self.fetch_data_types_button, self.rename_selected_button]:
            button.setStyleSheet("""
                QPushButton {
                    background-color: #6c757d;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #5a6268;
                }
            """)
        
        header_layout.addWidget(self.fetch_results_button)
        header_layout.addWidget(self.fetch_data_types_button)
        header_layout.addWidget(self.rename_selected_button)
        
        layout.addLayout(header_layout)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Successful", "Original Function Name", "Matched Function Name", 
            "Signature", "Matched Binary", "Similarity", "Confidence"
        ])
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.itemSelectionChanged.connect(self.on_result_selection_changed)
        
        layout.addWidget(self.results_table)

        results_widget.setLayout(layout)
        return results_widget

    def search_collections(self):
        """Search for collections based on input"""
        search_term = self.search_input.text().strip()
        self.status_label.setText(f"Searching collections for: '{search_term}'...")
        
        try:
            self.current_collections = self.match_functions.search_collections(search_term)
            self.populate_collections_table()
            self.status_label.setText(f"Found {len(self.current_collections)} collections")
        except Exception as e:
            log_error(f"RevEng.AI | Error searching collections: {str(e)}")
            self.status_label.setText(f"Error searching collections: {str(e)}")
            QMessageBox.critical(self, "Search Error", f"Failed to search collections:\n{str(e)}")

    def populate_collections_table(self):
        """Populate the collections table with search results"""
        self.collections_table.setRowCount(len(self.current_collections))
        
        for row, collection in enumerate(self.current_collections):
            # Name
            name_item = QTableWidgetItem(collection.get("name", ""))
            self.collections_table.setItem(row, 0, name_item)
            
            # Type
            type_item = QTableWidgetItem(collection.get("type", "Collection"))
            self.collections_table.setItem(row, 1, type_item)
            
            # Date
            date_item = QTableWidgetItem(collection.get("date", ""))
            self.collections_table.setItem(row, 2, date_item)
            
            # Model Name
            model_item = QTableWidgetItem(collection.get("model_name", ""))
            self.collections_table.setItem(row, 3, model_item)
            
            # Owner
            owner_item = QTableWidgetItem(collection.get("owner", ""))
            self.collections_table.setItem(row, 4, owner_item)

    def start_matching(self):
        """Start the function matching process"""
        distance_threshold = self.distance_spinbox.value()
        max_matches = self.max_matches_spinbox.value()
        
        log_info("RevEng.AI | Starting function matching process")
        
        # Create and show progress dialog
        self.progress = create_progress_dialog(self, "RevEng.AI Match Functions", "Matching functions...")
        
        # Create and start matching thread
        self.match_thread = MatchFunctionsThread(
            self.match_functions, 
            self.bv, 
            distance_threshold, 
            max_matches
        )
        self.match_thread.finished.connect(self.on_matching_finished)
        self.match_thread.start()
        
        self.progress.show()
        self.status_label.setText("Matching functions...")

    def on_matching_finished(self, success, data):
        """Handle matching completion"""
        self.progress.close()
        
        if success:
            self.current_matches = data
            self.populate_results_table()
            
            # Switch to results tab
            self.tab_widget.setCurrentIndex(1)
            
            # Update status
            successful_count = sum(1 for match in self.current_matches if match.get("successful", False))
            total_count = len(self.current_matches)
            skipped_count = total_count - successful_count
            
            self.results_label.setText(
                f"Total Functions Analyzed: {total_count} | "
                f"Successful Analyses: {successful_count} | "
                f"Skipped Analyses: {skipped_count}"
            )
            
            self.status_label.setText(f"Matching completed. Found {successful_count} successful matches.")
            
            QMessageBox.information(
                self,
                "RevEng.AI Match Functions",
                f"Function matching completed successfully!\n"
                f"Total functions analyzed: {total_count}\n"
                f"Successful matches: {successful_count}\n"
                f"Skipped: {skipped_count}",
                QMessageBox.Ok
            )
        else:
            log_error(f"RevEng.AI | Function matching failed: {data}")
            self.status_label.setText(f"Matching failed: {data}")
            QMessageBox.critical(
                self,
                "RevEng.AI Match Functions Error",
                f"Failed to match functions:\n{data}",
                QMessageBox.Ok
            )

    def populate_results_table(self):
        """Populate the results table with function matches"""
        self.results_table.setRowCount(len(self.current_matches))
        
        for row, match in enumerate(self.current_matches):
            # Successful (checkbox)
            successful_item = QTableWidgetItem()
            successful_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            successful_item.setCheckState(Qt.Checked if match.get("successful", False) else Qt.Unchecked)
            self.results_table.setItem(row, 0, successful_item)
            
            # Original Function Name
            original_item = QTableWidgetItem(match.get("original_name", ""))
            self.results_table.setItem(row, 1, original_item)
            
            # Matched Function Name
            matched_item = QTableWidgetItem(match.get("matched_name", "N/A"))
            self.results_table.setItem(row, 2, matched_item)
            
            # Signature
            signature_item = QTableWidgetItem(match.get("signature", "N/A"))
            self.results_table.setItem(row, 3, signature_item)
            
            # Matched Binary
            binary_item = QTableWidgetItem(match.get("matched_binary", "N/A"))
            self.results_table.setItem(row, 4, binary_item)
            
            # Similarity
            similarity = match.get("similarity", 0.0)
            similarity_item = QTableWidgetItem(f"{(1.0 - similarity) * 100:.2f}%")
            self.results_table.setItem(row, 5, similarity_item)
            
            # Confidence
            confidence_item = QTableWidgetItem(f"{match.get('confidence', 0.0):.2f}%")
            self.results_table.setItem(row, 6, confidence_item)

    def on_result_selection_changed(self):
        """Handle result selection change"""
        selected_rows = set()
        for item in self.results_table.selectedItems():
            selected_rows.add(item.row())
        
        # Enable/disable rename button based on selection
        self.rename_selected_button.setEnabled(len(selected_rows) > 0)

    def closeEvent(self, event):
        """Handle dialog close event"""
        self.accept() 