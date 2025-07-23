from binaryninja import log_info, log_error
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTabWidget, QMessageBox, QCheckBox, QGroupBox, QSlider)
from PySide6.QtCore import Qt, QCoreApplication
from revengai.utils import create_progress_dialog
from revengai.utils.data_thread import DataThread
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
        footer_layout = self.create_footer_layout()

        self.search_tab = SearchTab(self.match_functions, self.bv, self.status_label)
        self.tab_widget.addTab(self.search_tab, "Search")
        
        self.results_tab = ResultTab(self.match_functions, self.bv, self.status_label)
        self.tab_widget.addTab(self.results_tab, "Results")
        
        main_layout.addWidget(self.tab_widget)
        main_layout.addLayout(footer_layout)

        self.setLayout(main_layout)

    def create_footer_layout(self):
        footer_layout = QVBoxLayout()

        settings_group = QGroupBox()
        settings_layout = QVBoxLayout()

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
        
        self.confidence_value_label = QLabel("90")
        self.confidenceSlider.valueChanged.connect(lambda value: self.confidence_value_label.setText(str(value)))
        confidence_layout.addWidget(self.confidence_value_label)
        
        settings_layout.addLayout(confidence_layout)
        
        self.debug_symbols_checkbox = QCheckBox("Limit Matches to Debug Symbols")
        self.debug_symbols_checkbox.setChecked(True)
        settings_layout.addWidget(self.debug_symbols_checkbox)
        
        settings_group.setLayout(settings_layout)
        footer_layout.addWidget(settings_group)

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
        confidence_threshold = self.confidenceSlider.value()
        
        log_info("RevEng.AI | Starting function matching process")
        
        self.progress = create_progress_dialog(self, "RevEng.AI Match Functions", "Matching functions...")
        self.progress.show()
        QCoreApplication.processEvents() 
        self.status_label.setText("Matching functions...")

        options = {
            "confidence_threshold": confidence_threshold,
            "selected_collections": self.search_tab.selected_collections,
            "debug_symbols": self.debug_symbols_checkbox.isChecked()
        }
        
        self.match_thread = DataThread(self.match_functions.match_functions, self.bv, options)
        self.match_thread.finished.connect(self.on_matching_finished)
        self.match_thread.start()   

    def start_renaming(self):
        log_info("RevEng.AI | Starting function renaming process")
        
        self.progress = create_progress_dialog(self, "RevEng.AI Rename Selected Functions", "Renaming Selected functions...")
        self.progress.show()
        QCoreApplication.processEvents() 
        self.status_label.setText("Renaming selected functions...")

        self.rename_thread = DataThread(
            self.match_functions.rename_functions, 
            self.bv, 
            self.results_tab.selected_results
        )
        self.rename_thread.finished.connect(self.on_renaming_finished)
        self.rename_thread.start()  

    def start_fetching_data_types(self):
        log_info("RevEng.AI | Starting function data type fetching process")
        
        try:
            self.progress = create_progress_dialog(self, "RevEng.AI Fetch Data Types", "Fetching data types...")
            self.progress.show()
            QCoreApplication.processEvents() 
            self.status_label.setText("Fetching data types...")

            if not hasattr(self.results_tab, 'selected_results') or not self.results_tab.selected_results:
                log_error("RevEng.AI | No current matches available for data type fetching")
                self.progress.close()
                QMessageBox.warning(self,"RevEng.AI Fetch Data Types","No function matches available. Please run 'Fetch Results' first.", QMessageBox.Ok)
                return

            self.fetch_data_types_thread = DataThread(self.match_functions.fetch_data_types, self.bv, self.results_tab.selected_results)
            self.fetch_data_types_thread.finished.connect(self.on_fetching_data_types_finished)
            self.fetch_data_types_thread.start()

            log_info(f"RevEng.AI | Fetching data types thread started")
            
        except Exception as e:
            log_error(f"RevEng.AI | Error starting data type fetching: {str(e)}")
            if hasattr(self, 'progress'):
                self.progress.close()
            QMessageBox.critical(self, "RevEng.AI Fetch Data Types Error", f"Failed to start data type fetching:\n{str(e)}", QMessageBox.Ok)

    def on_renaming_finished(self, success, data):
        self.progress.close()
        
        if success:
            log_info(f"RevEng.AI | Renaming completed: {data}")
            QMessageBox.information(self, "RevEng.AI Rename Functions",  f"{data}", QMessageBox.Ok)
        else:
            log_error(f"RevEng.AI | Renaming failed: {data}")
            self.status_label.setText(f"Renaming failed: {data}")
            QMessageBox.critical(self, "RevEng.AI Rename Functions Error", f"Failed to rename functions:\n{data}", QMessageBox.Ok)

    def on_matching_finished(self, success, data):
        self.progress.close()
        
        if success:
            self.results_tab.current_matches = data["data"]
            self.results_tab.populate_results_table()

            if len(self.results_tab.selected_results) > 0:
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
                
            self.tab_widget.setCurrentIndex(1)
            
            successful_count = data["matched"]
            skipped_count = data["skipped"]
            failed_count = data["failed"]
            total_count = successful_count + skipped_count + failed_count
            
            self.status_label.setText(f"Matching completed!")
            self.results_tab.status_label.setText(f"Total Functions Analyzed: {total_count} | Successful Analyses: {successful_count} | Skipped Analyses: {skipped_count}")
            QMessageBox.information(self, "RevEng.AI Match Functions", f"Function matching completed successfully!\nSuccessful matches: {successful_count}\nNot enough confidence: {failed_count}\nSkipped: {skipped_count}\nTotal functions analyzed: {total_count}", QMessageBox.Ok)
        else:
            log_error(f"RevEng.AI | Function matching failed: {data}")
            self.status_label.setText(f"Matching failed: {data}")
            QMessageBox.critical(self, "RevEng.AI Match Functions Error", f"Failed to match functions:\n{data}", QMessageBox.Ok)

    def on_fetching_data_types_finished(self, success, data):
        self.progress.close()
        
        if success:
            log_info(f"RevEng.AI | Data type fetching completed with {data['success_count']} functions having signatures")
            self.results_tab.update_current_matches_with_signatures(data["signatures"])
            #self.results_tab.populate_results_table()
            self.status_label.setText(f"Data type fetching completed!")
            self.results_tab.status_label.setText(f"Data type fetching completed: {data['success_count']} functions have signatures")
            QMessageBox.information(self, "RevEng.AI Fetch Data Types", f"Data types fetched successfully.\n{data['success_count']} function{'' if data['success_count'] == 1 else 's'} have signatures.", QMessageBox.Ok)
        else:
            log_error(f"RevEng.AI | Data type fetching failed: {data}")
            self.status_label.setText(f"Data type fetching failed: {data}")
            QMessageBox.critical(self, "RevEng.AI Fetch Data Types Error", f"Failed to fetch data types:\n{data}", QMessageBox.Ok)