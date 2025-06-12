from binaryninja import PluginCommand, log_info, BinaryViewType, log_error
from .config import Config
from .config_dialog import ConfigDialog
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread, pyqtSignal
import threading

class ConfigInitThread(QThread):
    finished = pyqtSignal(bool, str, object)  # success, message, bv
    
    def __init__(self, config, bv):
        super().__init__()
        self.config = config
        self.bv = bv
        
    def run(self):
        try:
            status, message = self.config.init_config(self.bv)
            self.finished.emit(status, message, self.bv)
        except Exception as e:
            self.finished.emit(False, str(e), self.bv)

class ConfigurationFeature():
    def __init__(self):
        self.config = Config()
        self._thread_lock = threading.Lock()
        self._active_threads = {}
        self._register_binary_view_event()
        log_info("RevEng.AI | Configuration Feature initialized")
        
    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Configure",
            "Configure RevEng.AI settings",
            self.show_configuration
        )
        log_info("RevEng.AI | Configuration Feature registered")

    def show_configuration(self, bv):
        log_info("RevEng.AI | Opening configuration wizard")
        wizard = ConfigDialog(self.config)
        wizard.exec_()

    def get_config(self):
        return self.config  
    
    def _register_binary_view_event(self):
        BinaryViewType.add_binaryview_initial_analysis_completion_event(self._add_binaryview_finalized_event) # TODO: Use binaryview_finalized_event instead, but without load 3 times
        # TODO: Nao usar binaryview_finalized_event para checkar creds, resulta em comandos nao carregando.q
        log_info("RevEng.AI | Registered binary view event handler")

    def _add_binaryview_finalized_event(self, bv):
        try:
            log_info(f"RevEng.AI | Binary view finalized: {bv.file.original_filename}")
            
            # Use thread-safe approach
            with self._thread_lock:
                # Cancel any existing thread for this binary
                binary_key = bv.file.original_filename
                if binary_key in self._active_threads:
                    old_thread = self._active_threads[binary_key]
                    if old_thread.isRunning():
                        old_thread.terminate()
                        old_thread.wait()
                
                # Create new thread for this binary
                thread = ConfigInitThread(self.config, bv)
                thread.finished.connect(self._on_config_init_finished)
                self._active_threads[binary_key] = thread
                thread.start()
                
        except Exception as e:
            log_error(f"RevEng.AI | Error in binary view event handler: {str(e)}")
    
    def _on_config_init_finished(self, status, message, bv):
        try:
            # Clean up thread reference
            with self._thread_lock:
                binary_key = bv.file.original_filename
                if binary_key in self._active_threads:
                    del self._active_threads[binary_key]
            
            if status:
                log_info("RevEng.AI | Configuration initialized successfully")
            elif message == "Binary not found in RevEng.AI, try processing the binary again.":
                QMessageBox.warning(
                    None,
                    "RevEng.AI - Binary Not Found",
                    "This binary has not been processed in the RevEng.AI platform yet.\n\n"
                    "Please upload and process the binary first using the 'RevEng.AI > Upload Binary' option "
                    "before using other RevEng.AI features.",
                    QMessageBox.Ok
                )
            else:
                log_error(f"RevEng.AI | Configuration initialization failed: {message}")
                
        except Exception as e:
            log_error(f"RevEng.AI | Error in config init finished handler: {str(e)}")

    
    def _add_binaryview_finalized_event_old(self, bv):
        try:
            log_info(f"RevEng.AI | Binary view finalized: {bv.file.original_filename}")
            status, message = self.config.init_config(bv)
            if status:
                log_info("RevEng.AI | Configuration initialized successfully")
            elif message == "Binary not found in RevEng.AI, try processing the binary again.":
                QMessageBox.warning(
                    None,
                    "RevEng.AI - Binary Not Found",
                    "This binary has not been processed in the RevEng.AI platform yet.\n\n"
                    "Please upload and process the binary first using the 'RevEng.AI > Upload Binary' option "
                    "before using other RevEng.AI features.",
                    QMessageBox.Ok
                )
            else:
                log_error(f"RevEng.AI | Configuration initialization failed: {message}")
        except Exception as e:
            log_error(f"RevEng.AI | Error in binary view event handler: {str(e)}")