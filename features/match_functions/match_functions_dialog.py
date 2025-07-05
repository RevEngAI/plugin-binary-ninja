from binaryninja import BinaryView, log_info, log_error
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QTabWidget, QWidget, QMessageBox,
                             QCheckBox, QDoubleSpinBox, QSpinBox, QGroupBox,
                             QSplitter, QTextEdit, QProgressBar, QSlider)
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QIcon
from revengai_bn.utils import create_progress_dialog
from revengai_bn.utils.data_thread import DataThread
from .tab_search import SearchTab
from .tab_result import ResultTab

class MatchFunctionsDialog(QDialog):
    def __init__(self, config, match_functions, bv):
        super().__init__()
        self.config = config
        self.match_functions = match_functions
        self.bv = bv
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("RevEng.AI: Match Functions")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)

        main_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        
        # Footer layout
        footer_layout = self.create_footer_layout()

        # Search tab
        self.search_tab = SearchTab(self.match_functions, self.bv, self.status_label)
        self.tab_widget.addTab(self.search_tab, "Search")
        
        # Results tab
        self.results_tab = ResultTab(self.match_functions, self.bv, self.status_label)
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

        # Confidence slider
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence:"))
        self.confidenceSlider = QSlider()
        self.confidenceSlider.setMaximum(100)
        self.confidenceSlider.setPageStep(5)
        self.confidenceSlider.setSliderPosition(90)
        self.confidenceSlider.setOrientation(Qt.Horizontal)
        self.confidenceSlider.setInvertedAppearance(False)
        self.confidenceSlider.setInvertedControls(False)
        self.confidenceSlider.setTickPosition(QSlider.TicksBothSides)
        self.confidenceSlider.setTickInterval(5)
        self.confidenceSlider.setObjectName("confidenceSlider")
        confidence_layout.addWidget(self.confidenceSlider)
        
        # Add confidence value label
        self.confidence_value_label = QLabel("90")
        self.confidenceSlider.valueChanged.connect(lambda value: self.confidence_value_label.setText(str(value)))
        confidence_layout.addWidget(self.confidence_value_label)
        
        settings_layout.addLayout(confidence_layout)
        
        # Debug symbols checkbox
        self.debug_symbols_checkbox = QCheckBox("Limit Matches to Debug Symbols")
        self.debug_symbols_checkbox.setChecked(True)
        settings_layout.addWidget(self.debug_symbols_checkbox)
        
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
        self.fetch_data_types_button.clicked.connect(self.start_matching)
        self.rename_selected_button.clicked.connect(self.start_renaming)

        for button in [self.fetch_data_types_button, self.rename_selected_button]:
            button.setEnabled(False)
            button.setStyleSheet("""
                QPushButton {
                    background-color: #5a6268; 
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
            """) # another color #474b4e
        
        buttons_layout.addWidget(self.fetch_results_button)
        buttons_layout.addWidget(self.fetch_data_types_button)
        buttons_layout.addWidget(self.rename_selected_button)
        
        footer_layout.addLayout(buttons_layout)
        return footer_layout

    def start_matching(self):
        """Start the function matching process"""
        confidence_threshold = self.confidenceSlider.value()
        
        log_info("RevEng.AI | Starting function matching process")
        
        # Create and show progress dialog
        self.progress = create_progress_dialog(self, "RevEng.AI Match Functions", "Matching functions...")
        self.progress.show()
        QCoreApplication.processEvents() 
        self.status_label.setText("Matching functions...")

        options = {
            "confidence_threshold": confidence_threshold,
            "selected_collections": self.search_tab.selected_collections,
            "debug_symbols": self.debug_symbols_checkbox.isChecked()
        }
        
        # Create and start matching thread
        self.match_thread = DataThread(
            self.match_functions.match_functions, 
            self.bv, 
            options
        )
        self.match_thread.finished.connect(self.on_matching_finished)
        self.match_thread.start()   

    def start_renaming(self):
        """Start the function matching process"""
        log_info("RevEng.AI | Starting function renaming process")
        
        # Create and show progress dialog
        self.progress = create_progress_dialog(self, "RevEng.AI Rename Selected Functions", "Renaming Selected functions...")
        self.progress.show()
        QCoreApplication.processEvents() 
        self.status_label.setText("Renaming selected functions...")

        # Create and start matching thread
        self.rename_thread = DataThread(
            self.match_functions.rename_functions, 
            self.bv, 
            self.results_tab.selected_results
        )
        self.rename_thread.finished.connect(self.on_renaming_finished)
        self.rename_thread.start()  

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
        """Handle matching completion"""
        self.progress.close()
        
        if success:
            self.results_tab.current_matches = data["data"]
            self.results_tab.populate_results_table()
            self.rename_selected_button.setEnabled(len(self.results_tab.selected_results) > 0)
            self.fetch_data_types_button.setEnabled(len(self.results_tab.selected_results) > 0)
            
            # Switch to results tab
            self.tab_widget.setCurrentIndex(1)
            
            # Update status
            successful_count = data["matched"]
            skipped_count = data["skipped"]
            failed_count = data["failed"]
            total_count = successful_count + skipped_count + failed_count
            
            
            self.status_label.setText(
                f"Total Functions Analyzed: {total_count} | "
                f"Successful Analyses: {successful_count} | "
                f"Skipped Analyses: {skipped_count}"
            )
            
            #self.status_label.setText(f"Matching completed. Found {successful_count} successful matches.")
            
            QMessageBox.information(
                self,
                "RevEng.AI Match Functions",
                f"Function matching completed successfully!\n"
                f"Successful matches: {successful_count}\n"
                f"Failed: {failed_count}\n"
                f"Skipped: {skipped_count}\n"
                f"Total functions analyzed: {total_count}",
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

    def closeEvent(self, event):
        self.accept() 