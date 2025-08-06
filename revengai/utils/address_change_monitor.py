from binaryninja import BinaryView, log_info, log_error, Symbol, SymbolType, interaction
from binaryninja.interaction import InteractionHandler
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll, RE_get_analysis_id_from_binary_id, RE_get_functions_from_analysis, RE_poll_ai_decompilation, RE_begin_ai_decompilation
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Optional, Callable
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
from binaryninjaui import UIContext, UIContextNotification
from PySide6.QtCore import QTimer

class AddressChangeMonitor(UIContextNotification):
    """
    Monitors address changes in Binary Ninja's UI and calls a callback function
    when the user navigates to a new address in the decompiler view.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize the address change monitor.
        
        Args:
            callback: Optional callback function to call when address changes.
                     Should accept parameters: (context, view, address)
        """
        super().__init__()
        self.callback = callback
        self._registered = False
        self._last_address = None
        
        # Register for notifications
        self.register()
        
    def register(self):
        """Register this notification with the UI context"""
        if not self._registered:
            UIContext.registerNotification(self)
            self._registered = True
            log_info("RevEng.AI | AddressChangeMonitor registered for notifications")
    
    def unregister(self):
        """Unregister this notification from the UI context"""
        if self._registered:
            UIContext.unregisterNotification(self)
            self._registered = False
            log_info("RevEng.AI | AddressChangeMonitor unregistered from notifications")
    
    def set_callback(self, callback: Callable):
        """Set or update the callback function"""
        self.callback = callback
        log_info("RevEng.AI | AddressChangeMonitor callback updated")

    def OnAddressChange(self, context, view, frame, addr):
        """Called when the user navigates to a new address"""
        try:
            # Extract the address from the ViewLocation object
            current_addr = None
            
            # Handle ViewLocation object
            if hasattr(addr, 'getOffset'):
                current_addr = addr.getOffset()
            elif hasattr(addr, 'addr'):
                current_addr = addr.addr
            elif hasattr(addr, 'address'):
                current_addr = addr.address
            else:
                current_addr = addr
                
            
            # Avoid duplicate notifications for the same address
            if current_addr == self._last_address:
                return
                
            self._last_address = current_addr
            
            if self.callback:
                try:
                    self.callback(context, view, current_addr, "address_changed")
                except Exception as e:
                    log_error(f"RevEng.AI | Error in address change callback: {str(e)}")
        except Exception as e:
            log_error(f"RevEng.AI | Error processing address change: {str(e)}")
            log_info(f"RevEng.AI | OnAddressChange called with addr type: {type(addr)}")