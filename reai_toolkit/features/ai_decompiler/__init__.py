from PySide6.QtCore import Qt
from binaryninjaui import UIContext
from reai_toolkit.features.ai_decompiler.ai_decompiler import AIDecompiler
from PySide6.QtWidgets import QDockWidget
from reai_toolkit.utils import BaseAuthFeature
from reai_toolkit.features.ai_decompiler.ai_decompiler_dialog import AIDecompilerDialog
from binaryninja import PluginCommand, log_info, BinaryView, log_error

class AIDecompilerFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        self.ai_decompiler = AIDecompiler(config)
        self.dock_widget = None
        self.widget = None
        log_info("RevEng.AI | AIDecompiler Feature initialized")

    def register(self):
        PluginCommand.register_for_address(
            "RevEng.AI\\\u200b\u200b\u200bFunctions\\AI Decompiler",
            "Get the AI decompiler for the current function",
            self.show_ai_decompiler_dialog,
            self.is_valid
        )
        log_info("RevEng.AI | AIDecompiler Feature registered")

    def show_ai_decompiler_dialog(self, bv: BinaryView, func):
        try:
            log_info("RevEng.AI | Opening AI Decompiler Dock")
            
            ctx = UIContext.activeContext()
            if not ctx:
                log_error("RevEng.AI | No active UI context.")
                return

            main_win = ctx.mainWindow()
            if not main_win:
                log_error("RevEng.AI | No main window found.")
                return

            if self.dock_widget is not None and self.dock_widget.parent() is not None:
                self.dock_widget.raise_()
                log_info(f"RevEng.AI | AI Decompiler Dock already open, adding tab 0x{func:x}")
                if self.widget is not None:
                    self.widget.pre_tab_setup(bv, func)
                return
            
            self.dock_widget = QDockWidget("RevEng.AI | AI Decompiler", main_win)
            self.widget = AIDecompilerDialog(self.config, self.ai_decompiler, bv, func)
            self.dock_widget.setObjectName("RevEng.AI | AI Decompiler")
            self.dock_widget.setWidget(self.widget)
            main_win.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)
            self.dock_widget.raise_()
            
            self.dock_widget.visibilityChanged.connect(self.on_dock_closed)
            log_info("RevEng.AI | AI Decompiler Dock displayed.")

        except Exception as e:
            log_error(f"RevEng.AI | Error opening AI Decompiler Dock: {e}")
            return 

    def on_dock_closed(self, visible):
        if not visible:
            log_info("RevEng.AI | AI Decompiler Dock closed")
            self.dock_widget = None
            self.widget = None
            self.ai_decompiler.stop_address_tracking()

    def is_valid(self, bv: BinaryView, func):
        return self.config.is_configured == True and self.config.analysis_id is not None 