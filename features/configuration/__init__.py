from binaryninja import PluginCommand, log_info
from .config import Config
from .config_dialog import ConfigDialog
from ..base_auth_feature import BaseAuthFeature

class ConfigurationFeature():
    def __init__(self):
        self.config = Config()
        log_info("RevEng.AI | Configuration Feature initialized")
        
    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Configure",
            "Configure RevEng.AI settings",
            self.show_configuration
        )

    def show_configuration(self, bv):
        log_info("RevEng.AI | Opening configuration wizard")
        wizard = ConfigDialog(self.config)
        wizard.exec_()

    def get_config(self):
        return self.config