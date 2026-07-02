from reai_toolkit.features.configuration.config import Config
from reai_toolkit.features.configuration.config_dialog import ConfigDialog
from reai_toolkit.utils import DataThread
from PySide6.QtWidgets import QMessageBox
from binaryninja import PluginCommand, log_info, BinaryViewType, log_error

class ConfigurationFeature():
    def __init__(self):
        self.config = Config()
        self._init_threads = []
        self._register_binary_view_event()
        log_info("RevEng.AI | Configuration Feature initialized")
        
    def register(self):
        PluginCommand.register(
            "RevEng.AI\\​​​​Configure",
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
        BinaryViewType.add_binaryview_finalized_event(self._add_binaryview_finalized_event) 
        log_info("RevEng.AI | Registered binary view event handler")

    def _add_binaryview_finalized_event(self, bv):
        try:
            if bv.view_type == "Raw":
                return

            log_info(f"RevEng.AI | Binary view finalized: {bv.file.filename}")
            thread = DataThread(self.config.init_config, bv)
            thread.finished.connect(self._on_init_config_finished)
            thread.finished.connect(lambda *_: self._init_threads.remove(thread))
            self._init_threads.append(thread)
            thread.start()
        except Exception as e:
            log_error(f"RevEng.AI | Error in binary view event handler: {str(e)}")

    def _on_init_config_finished(self, status, message):
        if status:
            log_info("RevEng.AI | Configuration initialized successfully")
        elif message == "Binary not found in RevEng.AI, try processing the binary again.":
            QMessageBox.warning(
                None,
                "RevEng.AI - Binary Not Found",
                "This binary has not been processed in the RevEng.AI platform yet.\n\n"
                "Please upload and process the binary first using the 'RevEng.AI > Create new' option "
                "before using other RevEng.AI features.",
                QMessageBox.Ok
            )
        else:
            log_error(f"RevEng.AI | Configuration initialization failed: {message}")
