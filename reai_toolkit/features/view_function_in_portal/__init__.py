from reai_toolkit.utils import BaseAuthFeature
from reai_toolkit.features.view_function_in_portal.view_function_in_portal import ViewFunctionInPortal
from binaryninja import PluginCommand, log_info, BinaryView
from reai_toolkit.features.view_function_in_portal.view_function_in_portal_dialog import ViewFunctionInPortalDialog


class ViewFunctionInPortalFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.view_function_in_portal = ViewFunctionInPortal(config)
        log_info("RevEng.AI | ViewFunctionInPortal Feature initialized")

    def register(self):
        PluginCommand.register_for_address(
            "RevEng.AI\\\u200b\u200b\u200bFunctions\\\u200b\u200bView Function in Portal",
            "View the current function in the RevEng.AI portal",
            self.show_match_current_function_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | ViewFunctionInPortal Feature registered")

    def show_match_current_function_dialog(self, bv: BinaryView, func):
        log_info("RevEng.AI | Opening MatchCurrentFunction dialog")
        dialog = ViewFunctionInPortalDialog(self.config, self.view_function_in_portal, bv, func)
        dialog.exec_() 

    def is_valid(self, bv: BinaryView, func):
        return self.config.is_configured == True 