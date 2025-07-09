from binaryninja import BinaryView, log_info, log_error
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTabWidget, QWidget, QMessageBox,
                             QCheckBox, QDoubleSpinBox, QSpinBox, QGroupBox,
                             QSplitter, QTextEdit, QProgressBar, QSlider)
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QIcon
from revengai.utils import create_progress_dialog
from revengai.utils.data_thread import DataThread
from .tab_search import SearchTab
from .tab_result import ResultTab

class MatchCurrentFunctionDialog(QDialog):
    def __init__(self, config, match_current_function, bv, func):
        super().__init__()
        self.config = config
        self.match_current_function = match_current_function
        self.bv = bv
        self.func = func
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Match Current Function")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        main_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        
        # Footer layout
        footer_layout = self.create_footer_layout()

        # Search tab
        self.search_tab = SearchTab(self.match_current_function, self.bv, self.status_label)
        self.tab_widget.addTab(self.search_tab, "Search")
        
        # Results tab
        self.results_tab = ResultTab(self.match_current_function, self.bv, self.status_label)
        self.tab_widget.addTab(self.results_tab, "Results")
        
        main_layout.addWidget(self.tab_widget)

        main_layout.addLayout(footer_layout)

        # Status bar
        #self.status_label = QLabel("Ready")
        #main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

    def create_footer_layout(self):
        footer_layout = QVBoxLayout()

        # Match settings section
        settings_group = QGroupBox()
        settings_layout = QVBoxLayout()

        # similarity slider
        similarity_layout = QHBoxLayout()
        similarity_layout.addWidget(QLabel("Similarity:"))
        self.similaritySlider = QSlider()
        self.similaritySlider.setMaximum(100)
        self.similaritySlider.setPageStep(5)
        self.similaritySlider.setSliderPosition(90)
        self.similaritySlider.setOrientation(Qt.Horizontal)
        self.similaritySlider.setInvertedAppearance(False)
        self.similaritySlider.setInvertedControls(False)
        self.similaritySlider.setTickPosition(QSlider.TicksBothSides)
        self.similaritySlider.setTickInterval(5)
        self.similaritySlider.setObjectName("similaritySlider")
        similarity_layout.addWidget(self.similaritySlider)
        
        # Add similarity value label
        self.similarity_value_label = QLabel("90")
        self.similaritySlider.valueChanged.connect(lambda value: self.similarity_value_label.setText(str(value)))
        similarity_layout.addWidget(self.similarity_value_label)
        
        settings_layout.addLayout(similarity_layout)
        
        # Debug symbols checkbox
        self.debug_symbols_checkbox = QCheckBox("Limit Matches to Debug Symbols")
        self.debug_symbols_checkbox.setChecked(True)
        self.debug_symbols_spinbox = QSpinBox()
        self.debug_symbols_spinbox.setMinimum(1)
        self.debug_symbols_spinbox.setMaximum(20)
        self.debug_symbols_spinbox.setValue(5)
        self.debug_symbols_spinbox.setSuffix(" Functions")
        self.debug_symbols_spinbox.setPrefix("Limit to ")
        self.debug_symbols_spinbox.setFixedWidth(165)

        debug_symbols_layout = QHBoxLayout()
        debug_symbols_layout.addWidget(self.debug_symbols_checkbox)
        debug_symbols_layout.addWidget(self.debug_symbols_spinbox)
        settings_layout.addLayout(debug_symbols_layout)
        
        settings_group.setLayout(settings_layout)
        footer_layout.addWidget(settings_group)

        # Buttons layout
        buttons_layout = QHBoxLayout()

        self.status_label = QLabel("Ready!")
        buttons_layout.addWidget(self.status_label)
        buttons_layout.addStretch()
        
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
        
        self.fetch_results_button.clicked.connect(self.start_matching)
        self.fetch_data_types_button.clicked.connect(self.start_fetching_data_types)
        self.rename_selected_button.clicked.connect(self.start_renaming)

        for button in [self.fetch_data_types_button, self.rename_selected_button]:
            button.setEnabled(False)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #474b4e; 
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
            """) 
        
        buttons_layout.addWidget(self.fetch_results_button)
        buttons_layout.addWidget(self.fetch_data_types_button)
        buttons_layout.addWidget(self.rename_selected_button)
        
        footer_layout.addLayout(buttons_layout)
        return footer_layout

    def start_matching(self):
        """Start the current function matching process"""
        similarity_threshold = self.similaritySlider.value()
        
        log_info("RevEng.AI | Starting current function matching process")
        
        # Create and show progress dialog
        self.progress = create_progress_dialog(self, "RevEng.AI Match Current Function", "Matching current function...")
        self.progress.show()
        QCoreApplication.processEvents() 
        self.status_label.setText("Matching current function...")

        options = {
            "similarity_threshold": similarity_threshold,
            "selected_collections": self.search_tab.selected_collections,
            "debug_symbols": self.debug_symbols_checkbox.isChecked(),
            "debug_symbols_count": self.debug_symbols_spinbox.value(),
            "function": self.func
        }
        
        # Create and start matching thread
        self.match_thread = DataThread(
            self.match_current_function.match_functions, 
            self.bv, 
            options
        )
        self.match_thread.finished.connect(self.on_matching_finished)
        self.match_thread.start()   

    def start_renaming(self):
        """Start the current function renaming process"""
        log_info("RevEng.AI | Starting current function renaming process")
        
        # Check if a result is selected
        if not self.results_tab.selected_result:
            QMessageBox.warning(
                self,
                "RevEng.AI Rename Function",
                "Please select a function match first.",
                QMessageBox.Ok
            )
            return
        
        # Create and show progress dialog
        self.progress = create_progress_dialog(self, "RevEng.AI Rename Selected Function", "Renaming selected function...")
        self.progress.show()
        QCoreApplication.processEvents() 
        self.status_label.setText("Renaming selected function...")

        # Create and start matching thread - pass single result as list for compatibility
        self.rename_thread = DataThread(
            self.match_current_function.rename_function, 
            self.bv, 
            self.results_tab.selected_result
        )
        self.rename_thread.finished.connect(self.on_renaming_finished)
        self.rename_thread.start()  

    def start_fetching_data_types(self):
        log_info("RevEng.AI | Starting current function data type fetching process")
        try:

            # Create and show progress dialog
            self.progress = create_progress_dialog(self, "RevEng.AI Fetch Data Types", "Fetching data types...")
            self.progress.show()
            QCoreApplication.processEvents() 
            self.status_label.setText("Fetching data types...")

            self.fetch_data_types_thread = DataThread(
                self.match_current_function.fetch_data_types,
                self.bv,
                self.results_tab.current_matches
            )
            self.fetch_data_types_thread.finished.connect(self.on_fetching_data_types_finished)
            self.fetch_data_types_thread.start()

            log_info(f"RevEng.AI | Fetching data types thread started")
            
        except Exception as e:
            log_error(f"RevEng.AI | Error starting data type fetching: {str(e)}")
            if hasattr(self, 'progress'):
                self.progress.close()
            QMessageBox.critical(
                self,
                "RevEng.AI Fetch Data Types Error",
                f"Failed to start data type fetching:\n{str(e)}",
                QMessageBox.Ok
            )

    def on_renaming_finished(self, success, data):
        """Handle renaming completion"""
        self.progress.close()
        if success:
            log_info(f"RevEng.AI | Renaming completed: {data}")
            QMessageBox.information(
                self,
                "RevEng.AI Rename Functions",
                f"{data}",
                QMessageBox.Ok
            )
        else:
            log_error(f"RevEng.AI | Renaming failed: {data}")
            self.status_label.setText(f"Renaming failed: {data}")
            QMessageBox.critical(
                self,
                "RevEng.AI Rename Functions Error",
                QMessageBox.Ok
            )

    def on_matching_finished(self, success, data):
        self.progress.close()
        
        if success:
            self.results_tab.current_matches = data
            self.results_tab.populate_results_table()

            if len(self.results_tab.current_matches) > 0:
                for button in [self.fetch_data_types_button, self.rename_selected_button]:
                    button.setEnabled(True)
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
                
            
            # Switch to results tab
            self.tab_widget.setCurrentIndex(1)
            
            #self.status_label.setText(f"Matching completed. Found {successful_count} successful matches.")
            
            QMessageBox.information(
                self,
                "RevEng.AI Match Current Function",
                f"Current function matching completed successfully!\n"
                f"Total functions found: {len(data)}",
                QMessageBox.Ok
            )
        else:
            log_error(f"RevEng.AI | Current function matching failed: {data}")
            self.status_label.setText(f"Matching failed: {data}")
            QMessageBox.critical(
                self,
                "RevEng.AI Match Current Function Error",
                f"Failed to match current function:\n{data}",
                QMessageBox.Ok
            )

    def on_fetching_data_types_finished(self, success, data):
        """Handle data type fetching completion"""
        self.progress.close()
        
        if success:
            log_info(f"RevEng.AI | Data type fetching completed with {data['success_count']} functions having signatures")
            self.results_tab.update_current_matches_with_signatures(data["signatures"])
            #self.results_tab.populate_results_table()
            self.status_label.setText(f"Data type fetching completed: {data['success_count']} functions have signatures")

            QMessageBox.information(
                self,
                "RevEng.AI Fetch Data Types",
                f"Data types fetched successfully.\n{data['success_count']} function{'' if data['success_count'] == 1 else 's'} have signatures.",
                QMessageBox.Ok
            )
        else:
            log_error(f"RevEng.AI | Data type fetching failed: {data}")
            self.status_label.setText(f"Data type fetching failed: {data}")
            QMessageBox.critical(
                self,
                "RevEng.AI Fetch Data Types Error",
                f"Failed to fetch data types:\n{data}",
                QMessageBox.Ok
            )

    """
    def closeEvent(self, event):
        self.accept() 
    """ 