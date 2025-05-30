from binaryninja import log_info
from .features import ConfigurationFeature
from .features import UploadFeature

class RevengAIPlugin:
    def __init__(self):
        log_info("Initializing RevEng.AI Plugin")
        self.config_feature = ConfigurationFeature()
        self.upload_feature = UploadFeature(self.config_feature.get_config())
        self._register_features()
        
    def _register_features(self):
        self.config_feature.register()
        self.upload_feature.register()
        