from reai_toolkit.features.auto_unstrip.auto_unstrip import AutoUnstrip
from reai_toolkit.utils import BaseAuthFeature
from reai_toolkit.features.auto_unstrip.auto_unstrip_dialog import AutoUnstripDialog
from binaryninja import PluginCommand, log_info, BinaryView

class AutoUnstripFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.auto_unstrip = AutoUnstrip(config)
        log_info("RevEng.AI | AutoUnstrip Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\4 - Auto Unstrip",
            "Attempt to recover stripped function names",
            self.show_auto_unstrip_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | AutoUnstrip Feature registered")

    def show_auto_unstrip_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening AutoUnstrip dialog")
        dialog = AutoUnstripDialog(self.config, self.auto_unstrip, bv)
        dialog.exec_()
    
