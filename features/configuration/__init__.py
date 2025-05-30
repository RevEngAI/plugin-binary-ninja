from binaryninja import PluginCommand, log_info
from .config import Config
from .config_dialog import ApiKeyWizard

class ConfigurationFeature:
    def __init__(self):
        self.config = Config()
        log_info("RevEng.AI Configuration Feature initialized")
        
    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Configure",
            "Configure RevEng.AI settings",
            self.show_configuration
        )
        log_info("RevEng.AI Configuration Feature registered")
        
    def show_configuration(self, bv):
        log_info("Opening RevEng.AI configuration wizard")
        wizard = ApiKeyWizard(self.config)
        wizard.exec_()
        
    def get_config(self):
        return self.config