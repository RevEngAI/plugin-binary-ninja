from binaryninja import PluginCommand, log_info, log_error
from .upload import BinaryUploader
from .upload_dialog import UploadDialog
from ...utils.config_validator import validate_config

class UploadFeature:
    def __init__(self, config=None):
        self.config = config
        self.uploader = BinaryUploader(config)
        log_info("RevEng.AI Process Feature initialized")
        
    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Process Binary",
            "Process current binary to RevEng.AI for analysis",
            self.show_upload_dialog
        )
        log_info("RevEng.AI Process feature registered")
        
    def show_upload_dialog(self, bv):
        if not validate_config(self.config):
            return
        dialog = UploadDialog(self.config, self.uploader, bv)
        if dialog.exec() == UploadDialog.Accepted:
            self.uploader.upload_binary(bv, dialog.get_upload_options())