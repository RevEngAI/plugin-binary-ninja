from binaryninja import PluginCommand, log_info, BinaryView
from .upload import BinaryUploader
from .upload_dialog import UploadDialog
from revengai.utils import BaseAuthFeature

class UploadFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.uploader = BinaryUploader(config)
        log_info("RevEng.AI | Process Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Process Binary",
            "Process current binary to RevEng.AI for analysis",
            self.show_upload_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | Process Feature registered")

    def show_upload_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening process dialog")
        dialog = UploadDialog(self.config, self.uploader, bv)
        dialog.exec()