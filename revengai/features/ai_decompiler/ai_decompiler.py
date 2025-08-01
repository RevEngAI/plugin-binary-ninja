from binaryninja import BinaryView, log_info, log_error, Symbol, SymbolType, interaction
from binaryninja.interaction import InteractionHandler
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll, RE_get_analysis_id_from_binary_id, RE_get_functions_from_analysis, RE_poll_ai_decompilation, RE_begin_ai_decompilation
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import math
from revengai.utils.datatypes import apply_data_types as apply_data_types_util
import time
from revengai.utils import rename_function as rename_function_util, get_function_id_by_addr as get_function_id_by_addr_util
from libbs.api import DecompilerInterface
from libbs.decompilers.binja.interface import BinjaInterface
from libbs.artifacts import _art_from_dict
from libbs.artifacts import (
    Function,
    FunctionArgument,
    GlobalVariable,
    Enum,
    Struct,
    Typedef,
)
from revengai.utils.periodic_check import PeriodicChecker
from PySide6.QtWidgets import QPlainTextEdit
from binaryninja import BinaryView
from binaryninjaui import UIContext
from PySide6.QtCore import QTimer

class AIDecompiler:
    def __init__(self, config):
        self.config = config
        self._current_checker = None
        self._track_timer = None  # Add timer instance variable

    def stop_ai_decompiler(self):
        """Stop the current AI decompiler checking"""
        try:
            if self._current_checker:
                self._current_checker.stop()
                self._current_checker = None
                log_info("RevEng.AI | Stopped AI decompiler")
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping AI decompiler: {str(e)}")

    def stop_tracking(self):
        """Stop the active line tracking"""
        try:
            if self._track_timer:
                self._track_timer.stop()
                self._track_timer = None
                log_info("RevEng.AI | Stopped active line tracking")
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping active line tracking: {str(e)}")


    def start_ai_decompiler(self, bv: BinaryView, options: Dict) -> None:
        """Match functions from the binary against RevEng.AI database"""
        try:
            ClickMonitor()
            
            log_info("RevEng.AI | Starting function searching in portal")
            editor = options.get("editor")
            tab_name = options.get("tab_name")
            function = options.get("function")
            callback = options.get("callback")
            binary_id = self.config.get_binary_id(bv)
            function_id = get_function_id_by_addr_util(bv, function.start, binary_id)

            res = RE_poll_ai_decompilation(
                function_id,
                summarise=True,
            ).json()
            
            if not res.get("status", False):
                callback(editor, "AI Decompilation failed.")
                return
            
            poll_status = res.get("data").get("status", "uninitialised")
            log_info(f"RevEng.AI | Polling AI decompilation: {poll_status}")

            if poll_status == "uninitialised":
                log_info(f"RevEng.AI | Starting AI Decompilation for function at 0x{function.start:x}")

                try:
                    res2 = RE_begin_ai_decompilation(
                        function_id
                    ).json()
                except Exception as e:
                    log_error(f"RevEng.AI | Error beginning AI decompilation: {str(e)}")
                    callback(editor, "AI Decompilation failed.")
                    return
                
                if not res2.get("status", False):
                    callback(editor, "AI Decompilation failed.")
                    return

                log_info("RevEng.AI | AI Decompilation started")

                # Create PeriodicChecker instance (it's now a QObject)
                periodic_checker = PeriodicChecker()
                
                # Start the AI decompiler checking with proper parameters
                periodic_checker.start_ai_decompiler_checking(function_id, callback, editor, tab_name)
                
                # Store reference to prevent garbage collection
                self._current_checker = periodic_checker

            if poll_status == "success":
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function.start:x} is completed")
                callback(editor, res.get("data").get("decompilation"))

        except Exception as e:
            log_error(f"RevEng.AI | Error in AI decompiler: {str(e)}")
            return False, str(e)
        
from binaryninja import PluginCommand, BinaryView
from binaryninjaui import UIContext, UIContextNotification

class ClickMonitor(UIContextNotification):
    def __init__(self):
        log_info("RevEng.AI | ClickMonitor initialized")
        super().__init__()
        log_info(f"RevEng.AI | class ClickMonitor")
        for nome in dir(self):
            attr = getattr(self, nome)
            if callable(attr) and not nome.startswith("__") and not nome.startswith("On"):
                log_info(f"RevEng.AI | {nome}")
        UIContext.registerNotification(self)

    def OnViewChanged(self, context, view):
        log_info(f"RevEng.AI | View changed: {view}")

    def OnAddressChanged(self, context, view, addr):
        log_info(f"RevEng.AI | User navigated to address: {hex(addr)}")

