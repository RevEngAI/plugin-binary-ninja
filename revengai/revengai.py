from binaryninja import log_info
from .features import ConfigurationFeature
from .features import UploadFeature
from .features import AutoUnstripFeature
from .features import ChooseSourceFeature
from .features import MatchFunctionsFeature
from .features import MatchCurrentFunctionFeature

class RevengAIPlugin:
    def __init__(self):
        log_info("RevEng.AI | Initializing plugin")
        self.config_feature = ConfigurationFeature()
        self.upload_feature = UploadFeature(self.config_feature.get_config())
        self.auto_unstrip_feature = AutoUnstripFeature(self.config_feature.get_config())
        self.choose_source_feature = ChooseSourceFeature(self.config_feature.get_config())
        self.match_functions_feature = MatchFunctionsFeature(self.config_feature.get_config())
        self.match_current_function_feature = MatchCurrentFunctionFeature(self.config_feature.get_config())
        self._register_features()
        
    def _register_features(self):
        log_info("RevEng.AI | Registering features")
        self.config_feature.register()
        self.upload_feature.register()
        self.auto_unstrip_feature.register()
        self.choose_source_feature.register()
        self.match_functions_feature.register()
        self.match_current_function_feature.register()
        