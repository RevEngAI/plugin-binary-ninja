from reai_toolkit.utils import BaseAuthFeature
from reai_toolkit.features.match_functions.match_functions import MatchFunctions
from reai_toolkit.features.match_functions.match_functions_dialog import MatchFunctionsDialog
from binaryninja import PluginCommand, log_info, BinaryView

class MatchFunctionsFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.match_functions = MatchFunctions(config)
        log_info("RevEng.AI | MatchFunctions Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\5 - Match Functions",
            "Search and match functions against RevEng.AI database",
            self.show_match_functions_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | MatchFunctions Feature registered")

    def show_match_functions_dialog(self, bv: BinaryView):
        log_info("RevEng.AI | Opening MatchFunctions dialog")
        dialog = MatchFunctionsDialog(self.config, self.match_functions, bv)
        dialog.exec_() 
