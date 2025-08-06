from threading import Timer
import threading
from os.path import basename
from typing import Optional
from binaryninja import log_info, log_error, BinaryView
from requests.exceptions import RequestException
from reait.api import RE_status, RE_poll_ai_decompilation
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

    def start_checking(self, binary_view: BinaryView, binary_id: int, callback, interval: float = 60) -> None:
        def _worker(bv: BinaryView, bid: int):
            try:
                response = RE_status(bv.file.filename, bid)
                if response.status_code != 200:
                    log_error(f"RevEng.AI | Error getting status: {response.status_code}")
                    return

                status = response.json().get("status")
                log_info(f"RevEng.AI | Current status for binary {bid}: {status}")

                if status in ("Queued", "Processing"):
                    if bv and bv.file and bv.file.filename:
                        self._current_timer = Timer(
                            interval,
                            _worker,
                            args=(bv, bid)
                        )
                        self._current_timer.start()
                        log_info(
                            f"RevEng.AI | Scheduled next status check for: {basename(bv.file.filename)} [{bid}]"
                        )
                else:
                    callback(binary_id)
                    log_info(f"RevEng.AI | Analysis completed with status: {status}")
                    QMessageBox.information(
                        None,
                        "RevEng.AI Analysis Complete",
                        f"Binary analysis completed!",
                        QMessageBox.Ok
                    )

            except RequestException as ex:
                log_error(f"RevEng.AI | Error getting binary analysis status: {str(ex)}")
            except Exception as ex:
                log_error(f"RevEng.AI | Unexpected error during status check: {str(ex)}")

        self.stop()

        self._current_timer = Timer(30, _worker, args=(binary_view, binary_id))
        self._current_timer.start()
        log_info(
            f"RevEng.AI | Started periodic status check for: {basename(binary_view.file.filename)} [{binary_id}]"
        )

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
            self._ai_decompiler_timer.start(30000)  # 1000 ms = 1 second
            
            log_info(f"RevEng.AI | Started AI decompiler periodic check for: {name}")
            
        except Exception as ex:
            log_error(f"RevEng.AI | Error starting AI decompiler check: {str(ex)}")
    
    def _ai_decompiler_worker(self, function_id: int, name: str, callback, editor: QPlainTextEdit):
        """Worker method that runs in a separate thread via QTimer"""
        def worker_thread():
            try:
                res = RE_poll_ai_decompilation(
                    function_id,
                ).json()

                if not res.get("status", False):
                    log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} failed")
                    self.update_text_signal.emit(self._current_callback, f"AI Decompilation failed: {res.get('errors').get('message')}")
                    self.stop()
                    return
                
                poll_status = res.get("data").get("status", "uninitialised")
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} is {poll_status}")
                if poll_status != "success":
                    log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} is not completed")
                    return
                    
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function_id:x} is completed")
                self.stop()
                
                # Safely update UI through signal/slot mechanism
                self.update_text_signal.emit(self._current_callback, res.get("data").get("decompilation"))
                
            except Exception as ex:
                log_error(f"RevEng.AI | Error in AI decompiler worker: {str(ex)}")

        # Start the worker in a new thread
        thread = threading.Thread(target=worker_thread)
        thread.start()
                
                