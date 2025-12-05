from .choose_source import ChooseSource
from reai_toolkit.utils import BaseAuthFeature
from .choose_source_dialog import ChooseSourceDialog
from binaryninja import PluginCommand, log_info, BinaryView

class ChooseSourceFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.choose_source = ChooseSource(config)
        log_info("RevEng.AI | Attach to existing Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Analysis\​​Attach to existing",
            "Choose a source for the binary analysis",
            self.show_choose_source_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | Attach to existing Feature registered")

    def show_choose_source_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening Attach to existing dialog")
        dialog = ChooseSourceDialog(self.config, self.choose_source, bv)
        dialog.exec_()

    def is_valid(self, bv: BinaryView):
        return self.config.is_configured == True and self.config.analysis_id is None

