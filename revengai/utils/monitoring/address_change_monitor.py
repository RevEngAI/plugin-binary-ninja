from binaryninja import log_info, log_error
from typing import Optional, Callable
from binaryninjaui import UIContext, UIContextNotification

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