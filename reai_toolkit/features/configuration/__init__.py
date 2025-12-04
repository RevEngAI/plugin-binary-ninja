from reai_toolkit.features.configuration.config import Config
from reai_toolkit.features.configuration.config_dialog import ConfigDialog
from PySide6.QtWidgets import QMessageBox
from binaryninja import PluginCommand, log_info, BinaryViewType, log_error

class ConfigurationFeature():
    def __init__(self):
        self.config = Config()
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
            status, message = self.config.init_config(bv)
            if status:
                log_info("RevEng.AI | Configuration initialized successfully")
            elif message == "Binary not found in RevEng.AI, try processing the binary again.":
                QMessageBox.warning(
                    None,
                    "RevEng.AI - Binary Not Found",
                    "This binary has not been processed in the RevEng.AI platform yet.\n\n"
                    "Please upload and process the binary first using the 'RevEng.AI > Process Binary' option "
                    "before using other RevEng.AI features.",
                    QMessageBox.Ok
                )
            else:
                log_error(f"RevEng.AI | Configuration initialization failed: {message}")
        except Exception as e:
            log_error(f"RevEng.AI | Error in binary view event handler: {str(e)}")
