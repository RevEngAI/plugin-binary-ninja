from binaryninja import PluginCommand, log_info, BinaryView
from .choose_source import ChooseSource
from .choose_source_dialog import ChooseSourceDialog
from revengai_bn.utils import BaseAuthFeature

class ChooseSourceFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.choose_source = ChooseSource(config)
        log_info("RevEng.AI | Choose Source Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Choose Source",
            "Choose a source for the binary analysis",
            self.show_choose_source_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | Choose Source Feature registered")

    def show_choose_source_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening Choose Source dialog")
        dialog = ChooseSourceDialog(self.config, self.choose_source, bv)
        dialog.exec_()

