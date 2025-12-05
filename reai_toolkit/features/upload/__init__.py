from reai_toolkit.features.upload.upload import BinaryUploader
from reai_toolkit.features.upload.upload_dialog import UploadDialog
from reai_toolkit.utils import BaseAuthFeature
from binaryninja import PluginCommand, log_info, BinaryView

class UploadFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.uploader = BinaryUploader(config)
        log_info("RevEng.AI | Process Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Analysis\Create new",
            "Process current binary to RevEng.AI for analysis",
            self.show_upload_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | Process Feature registered")

    def show_upload_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening process dialog")
        dialog = UploadDialog(self.config, self.uploader, bv)
        dialog.exec()

    def is_valid(self, bv: BinaryView):
        return self.config.is_configured == True and self.config.analysis_id is None