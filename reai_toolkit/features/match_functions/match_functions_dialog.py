import os
from binaryninja import log_error, log_info
from PySide6.QtGui import QPixmap, QColor, QIcon
from PySide6.QtCore import Qt, QCoreApplication, QEvent, QRect, QSize
from reai_toolkit.utils import create_progress_dialog, DataThread
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QCheckBox, QMessageBox, QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem, QGroupBox, QLineEdit, QGridLayout, QDoubleSpinBox, QWidget, QFrame, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QSpacerItem, QSizePolicy
from reai_toolkit.utils.ui.collections_popup import CollectionsPopup
from revengai import FunctionMatchingRequest, FunctionMatchingFilters
from reai_toolkit.utils import create_cancellable_progress_dialog

class MatchFunctionsDialog(QDialog):
    def __init__(self, config, match_functions, bv):
        super().__init__()
        self.config = config
        self.match_functions = match_functions
        self.selected_results = []
        self.bv = bv
        self.init_ui()
        self.installEventFilter(self)

    def _show_collections_popup(self):
        log_info(f"RevEng.AI | Showing collections popup")
        self.collections_popup.show()

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            if isinstance(obj, QLineEdit):
                if obj.objectName() == "edit_collections":
                    self._show_collections_popup()
                elif obj.objectName() == "edit_binaries":
                    pass#self.match_functions.search_binaries(self.bv, obj.text())
            else:
                log_info(f"RevEng.AI | Mouse button press")
        return super().eventFilter(obj, event)
    

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Match Functions")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 950)

        self.collections_popup = CollectionsPopup(self.match_functions, self.bv, parent=self)

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
        title_label = QLabel("Function Matching")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        description_label = QLabel("Select functions and run ANN; Review results per function.")
        description_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        info_layout.addWidget(description_label)
        header_layout.addLayout(info_layout, stretch=1)
        
        layout.addLayout(header_layout)
        layout.addSpacing(20)

        
        functions_group = QGroupBox()
        #functions_group.setTitle("Function Selection")
        functions_group_layout = QVBoxLayout()
        """
        search_input_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search functions...")
        #self.search_input.returnPressed.connect(self._search_collections)
            
        self.select_all_button = QPushButton("Select All")
        #self.select_all_button.clicked.connect(self._search_collections)
        self.select_all_button.setStyleSheet(""
            QPushButton {
                background-color: #71797e;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                
            }
            QPushButton:hover {
                background-color: #7179ff;
            }
        "")

        self.clear_button = QPushButton("Clear")
        #self.clear_button.clicked.connect(self._search_collections)
        self.clear_button.setStyleSheet(""
            QPushButton {
                background-color: #71797e;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                
            }
            QPushButton:hover {
                background-color: #7179ff;
            }
        "")
            
        search_input_layout.addWidget(self.search_input)
        search_input_layout.addWidget(self.select_all_button)
        search_input_layout.addWidget(self.clear_button)
        """

        filter_group = QGroupBox()
        filter_group.setTitle("Filters")
        filter_grid_layout = QGridLayout()
        filter_grid_layout.setHorizontalSpacing(12)
        filter_grid_layout.setVerticalSpacing(8)

        lbl_collections = QLabel("Collections")

        self.edit_collections = QLineEdit()
        self.edit_collections.installEventFilter(self)
        self.edit_collections.setObjectName("edit_collections")
        self.edit_collections.setPlaceholderText("Search Collections")

        lbl_binaries = QLabel("Binaries")

        self.edit_binaries = QLineEdit()
        self.edit_binaries.installEventFilter(self)
        self.edit_binaries.setObjectName("edit_binaries")
        self.edit_binaries.setPlaceholderText("Search Binaries")

        lbl_confidence = QLabel("Confidence")
        self.edit_confidence = QDoubleSpinBox()
        self.edit_confidence.setMinimum(0)
        self.edit_confidence.setMaximum(100)
        self.edit_confidence.setValue(90)
        self.edit_confidence.setSuffix("%")
        self.edit_confidence.setSingleStep(1)
        self.edit_confidence.setDecimals(0)

        lbl_debug_symbols = QLabel("Debug Symbols")
        self.edit_debug_symbols = QCheckBox("Enable")
        self.edit_debug_symbols.setChecked(False)

        lbl_user_symbols = QLabel("User Debug Symbols")
        self.edit_user_symbols = QCheckBox("Enable")
        self.edit_user_symbols.setChecked(False)

        button_clear_filters = QPushButton("Reset")
        button_clear_filters.setStyleSheet("""
            QPushButton {
                background-color: #71797e;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)
        #button_clear_filters.clicked.connect(self.clear_filters)

        filter_grid_layout.addWidget(lbl_collections, 0, 0)
        filter_grid_layout.addWidget(self.edit_collections, 0, 1)
        filter_grid_layout.addWidget(lbl_binaries, 0, 2)
        filter_grid_layout.addWidget(self.edit_binaries, 0, 3)
        filter_grid_layout.addWidget(lbl_confidence, 1, 0)
        filter_grid_layout.addWidget(self.edit_confidence, 1, 1)
        filter_grid_layout.addWidget(lbl_debug_symbols, 1, 2)
        filter_grid_layout.addWidget(self.edit_debug_symbols, 1, 3)
        filter_grid_layout.addWidget(lbl_user_symbols, 2, 2)
        filter_grid_layout.addWidget(self.edit_user_symbols, 2, 3)
        filter_grid_layout.addWidget(button_clear_filters, 2, 0)
        filter_group.setLayout(filter_grid_layout)


        self.results_table = QTableWidget()
        self.results_table.setColumnCount(8)
        self.results_table.setHorizontalHeaderLabels([
            "Virtual Address", "Function Name", "Matched Function", "Signature", "Similarity", "Confidence", "Matched Hash", "Matched Binary"
        ])
        self.results_table.setSelectionMode(QAbstractItemView.NoSelection)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.verticalHeader().setVisible(False)

        #functions_group_layout.addLayout(search_input_layout)
        functions_group_layout.addWidget(filter_group)
        functions_group_layout.addSpacing(20)
        functions_group_layout.addWidget(self.results_table)

        functions_group.setLayout(functions_group_layout)
        layout.addWidget(functions_group)

        layout.addSpacing(20)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Match Functions")
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
        self.save_button.clicked.connect(self.start_matching)
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


    def start_matching(self):
        log_info("RevEng.AI | Starting function matching process")
        
        self.progress = create_cancellable_progress_dialog(self, "RevEng.AI Match Functions", "Matching functions...", self.match_functions.cancel)
        self.progress.show()
        QCoreApplication.processEvents() 

        options = {
            "confidence_threshold": self.edit_confidence.value(),
            "selected_collections": self.edit_collections.text(),
            "selected_binaries": self.edit_binaries.text(),
            "debug_symbols": self.edit_debug_symbols.isChecked(),
            "user_symbols": self.edit_user_symbols.isChecked(),
            "populate_table_function": self.populate_results_table
        }
        
        self.match_thread = DataThread(self.match_functions.match_functions, self.bv, options, self.match_functions.clear_cancelled)
        self.match_thread.finished.connect(self.on_matching_finished)
        self.match_thread.start()   

    def on_matching_finished(self, success, data):
        self.progress.close()
        
        if success:
            self.populate_results_table(data["data"])
            self.all_results = data["data"]
            successful_count = data["matched"]
            skipped_count = data["skipped"]
            failed_count = data["failed"]
            total_count = successful_count + skipped_count + failed_count
            
            #QMessageBox.information(self, "RevEng.AI Match Functions", f"Function matching completed successfully!\nSuccessful matches: {successful_count}\nNot enough confidence: {failed_count}\nSkipped: {skipped_count}\nTotal functions analyzed: {total_count}", QMessageBox.Ok)
            self.start_fetching_data_types()

        else:
            self.populate_results_table([])
            log_error(f"RevEng.AI | Function matching failed: {data}")
            QMessageBox.critical(self, "RevEng.AI Match Functions Error", f"Failed to match functions:\n{data}", QMessageBox.Ok)
    
    def populate_results_table(self, results):
        self.selected_results.clear()
        
        self.results_table.setRowCount(0)
        self.results_table.setRowCount(len(results))
        
        for row, match in enumerate(results):
            column_data = [
                "function_address",
                "function_name",
                "matched_function_name",
                "signature",
                "similarity",
                "confidence",
                "matched_hash",
                "matched_binary_name"
            ] 

            for column, field in enumerate(column_data, start=0):
                value = match.get(field, "N/A")
                if field == "function_address":
                    if isinstance(value, int):
                        value = f"0x{value:x}"
                    else:
                        value = value
                
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if field == "similarity" or field == "confidence":
                    if float(value[:-1]) >= 90.0:
                        item.setForeground(QColor(0, 255, 0))
                    elif float(value[:-1]) >= 50.0:
                        item.setForeground(QColor(255, 255, 0))
                    else:
                        item.setForeground(QColor(255, 0, 0))
                
                elif field == "signature":
                    if value == "N/A":
                        icon_path = f"{os.path.dirname(__file__)}/../../images/failed.png"
                        item.setToolTip("No signature found")
                    else:
                        icon_path = f"{os.path.dirname(__file__)}/../../images/success.png"
                        item.setToolTip(value)
                    item.setIcon(QIcon(icon_path))
                    #item.setIconAlignment(Qt.AlignCenter)
                    item.setText("")
                else:
                    item.setToolTip(value)
                self.results_table.setItem(row, column, item)
            
            if match.get("icon_text", "Failed") == "Success":
                self.selected_results.append(match)

    def start_fetching_data_types(self):
        log_info("RevEng.AI | Starting function data type fetching process")
        
        try:
            self.progress = create_cancellable_progress_dialog(self, "RevEng.AI Fetch Data Types", "Fetching data types...", self.match_functions.cancel)
            self.progress.show()
            QCoreApplication.processEvents() 

            if not hasattr(self, 'selected_results') or not self.selected_results:
                log_error("RevEng.AI | No current matches available for data type fetching")
                self.progress.close()
                QMessageBox.warning(self,"RevEng.AI Fetch Data Types","No function matches available. Please run 'Fetch Results' first.", QMessageBox.Ok)
                return

            self.fetch_data_types_thread = DataThread(self.match_functions.fetch_data_types, self.bv, self.selected_results, self.match_functions.clear_cancelled)
            self.fetch_data_types_thread.finished.connect(self.on_fetching_data_types_finished)
            self.fetch_data_types_thread.start()

            log_info(f"RevEng.AI | Fetching data types thread started")
            
        except Exception as e:
            log_error(f"RevEng.AI | Error starting data type fetching: {str(e)}")
            if hasattr(self, 'progress'):
                self.progress.close()
            QMessageBox.critical(self, "RevEng.AI Fetch Data Types Error", f"Failed to start data type fetching:\n{str(e)}", QMessageBox.Ok)

    def on_fetching_data_types_finished(self, success, data):
        self.progress.close()
        
        if success:
            log_info(f"RevEng.AI | Data type fetching completed with {data['success_count']} functions having signatures")
            for signature in data["signatures"]:
                for result in self.all_results:
                    if result["nearest_neighbor_id"] == signature["nearest_neighbor_id"]:
                        result["signature"] = signature["signature"]
                        result["data_types"] = signature["data_types"]
                        result["signature_data"] = signature["signature_data"]
                        break
            self.populate_results_table(self.all_results)
            QMessageBox.information(self, "RevEng.AI Fetch Data Types", f"Data types fetched successfully.\n{data['success_count']} function{'' if data['success_count'] == 1 else 's'} have signatures.", QMessageBox.Ok)
        else:
            log_error(f"RevEng.AI | Data type fetching failed: {data}")
            QMessageBox.critical(self, "RevEng.AI Fetch Data Types Error", f"Failed to fetch data types:\n{data}", QMessageBox.Ok)
