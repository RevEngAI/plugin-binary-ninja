from threading import Timer
import threading
from os.path import basename
from typing import Optional
from binaryninja import log_info, log_error, BinaryView
from requests.exceptions import RequestException
from reait.api import RE_status, RE_poll_ai_decompilation, RE_begin_ai_decompilation
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import QTimer, QObject, Signal

class PeriodicChecker(QObject):
    # Signal for thread-safe UI updates
    update_text_signal = Signal(object, str)
    
    def __init__(self):
        super().__init__()
        self._current_timer: Optional[Timer] = None
        self._ai_decompiler_timer: Optional[QTimer] = None
        self.number_of_clicks = 0
        self.flag = False
        # Connect signal to slot for safe UI updates
        self.update_text_signal.connect(self._update_text_slot)

    def _update_text_slot(self, callback, text):
        """Slot that runs in the main thread to safely update UI"""
        try:
            if hasattr(callback, '__call__'):
                # If callback is a function, call it with editor and text
                # We need to get the editor from somewhere - let's store it
                if hasattr(self, '_current_editor'):
                    callback(self._current_editor, text)
        except Exception as ex:
            log_error(f"RevEng.AI | Error updating UI: {str(ex)}")

    def stop(self):
        if self._current_timer:
            self._current_timer.cancel()
            self._current_timer = None
            log_info("RevEng.AI | Stopped periodic status check")
        
        if self._ai_decompiler_timer:
            self._ai_decompiler_timer.stop()
            self._ai_decompiler_timer = None
            log_info("RevEng.AI | Stopped AI decompiler periodic check")

    def start_ai_decompiler_checking(self, function_id: int, callback, editor: QPlainTextEdit, name: str) -> None:
        """Start periodic checking for AI decompiler with thread-safe UI updates"""
        try:

            # Store editor reference for the signal slot
            log_info(f"RevEng.AI | Starting AI decompiler periodic check for: {name}")
            self._current_editor = editor
            self._current_callback = callback
            
            # Stop any existing timer
            if self._ai_decompiler_timer:
                self._ai_decompiler_timer.stop()
            
            # Create QTimer for thread-safe execution
            self._ai_decompiler_timer = QTimer()
            self._ai_decompiler_timer.timeout.connect(lambda: self._ai_decompiler_worker(function_id, name, callback, editor))
            
            # Start the timer with 5 second intervals
            self._ai_decompiler_timer.start(1000)  # 1000 ms = 1 second
            
            log_info(f"RevEng.AI | Started AI decompiler periodic check for: {name}")
            
        except Exception as ex:
            log_error(f"RevEng.AI | Error starting AI decompiler check: {str(ex)}")
    def _ai_decompiler_worker(self, function_id: int, name: str, callback, editor: QPlainTextEdit):
        """Worker method that runs in a separate thread via QTimer"""
        try:
            if self.flag:
                log_info(f"RevEng.AI | AI Decompilation is already in progress")
                return
            self.flag = True
            res = RE_poll_ai_decompilation(
                function_id,
            ).json()
            

            if not res.get("status", False):
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} failed")
                raise Exception(f"AI Decompilation for function at 0x{function_id:x} failed")
            
            poll_status = res.get("data").get("status", "uninitialised")
            log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} is {poll_status}")
            
            if poll_status == "uninitialised":
                log_info(f"RevEng.AI | Starting AI Decompilation for function at 0x{function_id:x}")
                try:
                    res2 = RE_begin_ai_decompilation(
                        function_id
                    ).json()
                except Exception as e:
                    log_error(f"RevEng.AI | Error beginning AI decompilation: {str(e)}")
                    raise Exception(f"AI Decompilation for function at 0x{function_id:x} failed")
                
                if not res2.get("status", False):
                    raise Exception(f"AI Decompilation for function at 0x{function_id:x} failed")
                
            elif poll_status != "success":
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} is not completed")
                self.flag = False
                return
            
            self.flag = False
            log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} is completed")
            
            # Safely update UI through signal/slot mechanism
            self.update_text_signal.emit(self._current_callback, res.get("data").get("decompilation"))

            # Stop timer from main thread
            self.update_text_signal.emit(lambda x,y: self.stop(), "")

        except Exception as ex:
            self.flag = False
            log_error(f"RevEng.AI | Error in AI decompiler worker: {str(ex)}")
            self.update_text_signal.emit(self._current_callback, f"AI Decompilation failed: {ex}")
            # Stop timer from main thread
            self.update_text_signal.emit(lambda x,y: self.stop(), "")