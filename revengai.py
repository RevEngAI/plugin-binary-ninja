from binaryninja import log_info
from .features import ConfigurationFeature
from .features import UploadFeature
from .features import AutoUnstripFeature

class RevengAIPlugin:
    def __init__(self):
        log_info("RevEng.AI | Initializing plugin")
        self.config_feature = ConfigurationFeature()
        self.upload_feature = UploadFeature(self.config_feature.get_config())
        self.autounstrip_feature = AutoUnstripFeature(self.config_feature.get_config())
        self._register_features()
        
    def _register_features(self):
        log_info("RevEng.AI | Registering features")
        self.config_feature.register()
        self.upload_feature.register()
        self.autounstrip_feature.register()
        