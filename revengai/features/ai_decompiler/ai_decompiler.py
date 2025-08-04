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
    
    def OnViewChange(self, context, view, frame):
        """Called when the view changes"""
        log_info(f"RevEng.AI | OnViewChange called: {view}")
        if self.callback:
            try:
                self.callback(context, view, None, "view_changed")
            except Exception as e:
                log_error(f"RevEng.AI | Error in view change callback: {str(e)}")

    def OnAddressChange(self, context, view, frame, addr):
        """Called when the user navigates to a new address"""
        # addr is a ViewLocation object, not a simple integer
        try:
            # Extract the address from the ViewLocation object
            if hasattr(addr, 'addr'):
                current_addr = addr.addr
            elif hasattr(addr, 'address'):
                current_addr = addr.address
            else:
                current_addr = addr
                
            log_info(f"RevEng.AI | OnAddressChange called: {addr} (address: 0x{current_addr:x})")
            
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
            log_info(f"RevEng.AI | OnAddressChange called with addr type: {type(addr)}, value: {addr}")
    
    def OnFunctionChange(self, context, view, frame, func):
        """Called when the current function changes"""
        if func:
            log_info(f"RevEng.AI | OnFunctionChange called: {func.name} at 0x{func.start:x}")
            if self.callback:
                try:
                    self.callback(context, view, func.start, "function_changed")
                except Exception as e:
                    log_error(f"RevEng.AI | Error in function change callback: {str(e)}")

class TimerBasedAddressMonitor:
    """
    Alternative address monitor that uses a timer to periodically check
    the current address in the active context.
    """
    
    def __init__(self, callback: Optional[Callable] = None, interval: int = 100):
        """
        Initialize the timer-based address monitor.
        
        Args:
            callback: Optional callback function to call when address changes.
            interval: Polling interval in milliseconds (default: 100ms)
        """
        self.callback = callback
        self._last_address = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._check_address)
        self._interval = interval
        self._active = False
        
    def start(self):
        """Start monitoring address changes"""
        if not self._active:
            self._timer.start(self._interval)
            self._active = True
            log_info(f"RevEng.AI | TimerBasedAddressMonitor started (interval: {self._interval}ms)")
    
    def stop(self):
        """Stop monitoring address changes"""
        if self._active:
            self._timer.stop()
            self._active = False
            self._last_address = None
            log_info("RevEng.AI | TimerBasedAddressMonitor stopped")
    
    def set_callback(self, callback: Callable):
        """Set or update the callback function"""
        self.callback = callback
        log_info("RevEng.AI | TimerBasedAddressMonitor callback updated")
    
    def _check_address(self):
        """Check the current address and call callback if it changed"""
        try:
            ctx = UIContext.activeContext()
            if not ctx:
                return
                
            # Try to get the current address from the context
            current_addr = None
            
            # Method 1: Try to get from the current view
            try:
                view = ctx.getCurrentView()
                if view:
                    current_addr = view.getCurrentAddress()
            except:
                pass
            
            # Method 2: Try to get from the current function
            if current_addr is None:
                try:
                    func = ctx.getCurrentFunction()
                    if func:
                        current_addr = func.start
                except:
                    pass
            
            # Method 3: Try to get from the current binary view
            if current_addr is None:
                try:
                    bv = ctx.getCurrentBinaryView()
                    if bv:
                        # Get the current function's address
                        funcs = list(bv.functions)
                        if funcs:
                            current_addr = funcs[0].start
                except:
                    pass
            
            if current_addr is not None and current_addr != self._last_address:
                self._last_address = current_addr
                log_info(f"RevEng.AI | Timer detected address change to: 0x{current_addr:x}")
                
                if self.callback:
                    try:
                        self.callback(ctx, None, current_addr, "address_changed")
                    except Exception as e:
                        log_error(f"RevEng.AI | Error in timer-based address change callback: {str(e)}")
                        
        except Exception as e:
            log_error(f"RevEng.AI | Error in timer-based address check: {str(e)}")

class AIDecompiler:
    def __init__(self, config):
        self.config = config
        self._current_checker = None
        self._track_timer = None
        self._address_monitor = None  # Store the address monitor instance
        self._timer_monitor = None    # Store the timer-based monitor instance

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

    def start_address_tracking(self, callback: Optional[Callable] = None, use_timer: bool = True):
        """
        Start tracking address changes in the Binary Ninja UI.
        
        Args:
            callback: Optional callback function to call when address changes.
                     Should accept parameters: (context, view, address, change_type)
                     where change_type can be "address_changed", "function_changed", or "view_changed"
            use_timer: Whether to also use timer-based monitoring as a fallback
        """
        try:
            # Stop any existing monitors
            self.stop_address_tracking()
            
            # Create notification-based monitor
            self._address_monitor = AddressChangeMonitor(callback)
            log_info("RevEng.AI | Started notification-based address tracking")
            
            # Create timer-based monitor as fallback if requested
            if use_timer:
                self._timer_monitor = TimerBasedAddressMonitor(callback)
                self._timer_monitor.start()
                log_info("RevEng.AI | Started timer-based address tracking")
            
        except Exception as e:
            log_error(f"RevEng.AI | Error starting address tracking: {str(e)}")

    def stop_address_tracking(self):
        """Stop tracking address changes"""
        try:
            if self._address_monitor:
                self._address_monitor.unregister()
                self._address_monitor = None
                log_info("RevEng.AI | Stopped notification-based address tracking")
                
            if self._timer_monitor:
                self._timer_monitor.stop()
                self._timer_monitor = None
                log_info("RevEng.AI | Stopped timer-based address tracking")
                
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping address tracking: {str(e)}")

    def set_address_tracking_callback(self, callback: Callable):
        """
        Set or update the callback for address tracking.
        
        Args:
            callback: Function to call when address changes.
                     Should accept parameters: (context, view, address, change_type)
        """
        try:
            if self._address_monitor:
                self._address_monitor.set_callback(callback)
            if self._timer_monitor:
                self._timer_monitor.set_callback(callback)
            else:
                # If no monitor exists, create one
                self.start_address_tracking(callback)
        except Exception as e:
            log_error(f"RevEng.AI | Error setting address tracking callback: {str(e)}")

    def start_ai_decompiler(self, bv: BinaryView, options: Dict) -> None:
        """Match functions from the binary against RevEng.AI database"""
        try:
            # Example of how to use address tracking with AI decompiler
            def address_change_callback(context, view, addr, change_type):
                """Example callback for address changes"""
                if change_type == "address_changed" and addr is not None:
                    log_info(f"RevEng.AI | Address changed to 0x{addr:x} - could trigger AI decompilation here")
                    # You can add your custom logic here, such as:
                    # - Automatically starting AI decompilation for the new function
                    # - Updating UI elements
                    # - Triggering other analysis
                    
                    # Example: Get function at the new address
                    if bv:
                        functions = bv.get_functions_containing(addr)
                        if functions:
                            function = functions[0]
                            log_info(f"RevEng.AI | Function at new address: {function.name} at 0x{function.start:x}")
            
            # Start address tracking with both notification and timer-based monitoring
            self.start_address_tracking(address_change_callback, use_timer=True)
            
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

            if poll_status == "error":
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function.start:x} failed")
                callback(editor, "AI Decompilation failed.")

        except Exception as e:
            log_error(f"RevEng.AI | Error in AI decompiler: {str(e)}")
            return False, str(e)

# Legacy ClickMonitor class for backward compatibility
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

