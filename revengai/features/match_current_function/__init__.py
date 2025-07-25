from binaryninja import PluginCommand, log_info, BinaryView
from .match_current_function import MatchCurrentFunction
from .match_current_function_dialog import MatchCurrentFunctionDialog
from revengai.utils import BaseAuthFeature

class MatchCurrentFunctionFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.match_current_function = MatchCurrentFunction(config)
        log_info("RevEng.AI | MatchCurrentFunction Feature initialized")

    def register(self):
        PluginCommand.register_for_address(
            "RevEng.AI\\6 - Match Current Function",
            "Search and match the current function against RevEng.AI database",
            self.show_match_current_function_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | MatchCurrentFunction Feature registered")

    def show_match_current_function_dialog(self, bv: BinaryView, func):
        log_info("RevEng.AI | Opening MatchCurrentFunction dialog")
        dialog = MatchCurrentFunctionDialog(self.config, self.match_current_function, bv, func)
        dialog.exec_() 

    def is_valid(self, bv: BinaryView, func):
        return self.config.is_configured == True 