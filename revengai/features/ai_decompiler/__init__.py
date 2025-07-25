from binaryninja import PluginCommand, log_info, BinaryView
from .ai_decompiler import AIDecompiler
from .ai_decompiler_dialog import AIDecompilerDialog
from revengai.utils import BaseAuthFeature

class AIDecompilerFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.ai_decompiler = AIDecompiler(config)
        log_info("RevEng.AI | AIDecompiler Feature initialized")

    def register(self):
        PluginCommand.register_for_address(
            "RevEng.AI\\7 - AI Decompiler",
            "Get the AI decompiler for the current function",
            self.show_ai_decompiler_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | AIDecompiler Feature registered")

    def show_ai_decompiler_dialog(self, bv: BinaryView, func):
        log_info("RevEng.AI | Opening MatchCurrentFunction dialog")
        dialog = AIDecompilerDialog(self.config, self.ai_decompiler, bv, func)
        dialog.exec_() 

    def is_valid(self, bv: BinaryView, func):
        return self.config.is_configured == True 