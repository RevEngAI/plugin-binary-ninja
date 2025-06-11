from binaryninja import PluginCommand, log_info, BinaryViewType, log_error
from .config import Config
from .config_dialog import ConfigDialog

class ConfigurationFeature():
    def __init__(self):
        self.config = Config()
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
        BinaryViewType.add_binaryview_finalized_event(self._add_binaryview_finalized_event)
        log_info("RevEng.AI | Registered binary view event handler")

    def _add_binaryview_finalized_event(self, bv):
        try:
            log_info(f"RevEng.AI | Binary view finalized: {bv.file.original_filename}")
            self.config.init_config()
        except Exception as e:
            log_error(f"RevEng.AI | Error in binary view event handler: {str(e)}")