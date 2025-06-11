from binaryninja import PluginCommand, log_info, BinaryView
from .autounstrip import AutoUnstrip
from .autounstrip_dialog import AutoUnstripDialog
from revengai_bn.utils import BaseAuthFeature

class AutoUnstripFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.autounstrip = AutoUnstrip(config)
        log_info("RevEng.AI | AutoUnstrip Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\AutoUnstrip",
            "Attempt to recover stripped function names",
            self.show_autounstrip_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | AutoUnstrip Feature registered")

    def show_autounstrip_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening AutoUnstrip dialog")
        dialog = AutoUnstripDialog(self.config, self.autounstrip, bv)
        dialog.exec_()

