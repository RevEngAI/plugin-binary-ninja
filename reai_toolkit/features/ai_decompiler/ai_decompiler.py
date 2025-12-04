from typing import Dict, Optional, Callable
from binaryninja import BinaryView, log_info, log_error
import revengai
from reai_toolkit.utils import get_function_id_by_addr as get_function_id_by_addr_util, AddressChangeMonitor, AIDecompilerChecker

class AIDecompiler:
    def __init__(self, config):
        self.config = config
        self._current_checker = None
        self._track_timer = None
        self.tracking_enabled = False
        self._address_monitor = None
        self._timer_monitor = None
        self.dialog = None

    def stop_ai_decompiler(self):
        try:
            if self._current_checker:
                self._current_checker.stop()
                self._current_checker = None
                log_info("RevEng.AI | Stopped AI decompiler")
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping AI decompiler: {str(e)}")

    def stop_tracking(self):
        try:
            if self._track_timer:
                self._track_timer.stop()
                self._track_timer = None
                log_info("RevEng.AI | Stopped active line tracking")
        except Exception as e:
            log_error(f"RevEng.AI | Error stopping active line tracking: {str(e)}")

    def start_address_tracking(self, callback: Optional[Callable] = None, use_timer: bool = True):
        try:
            self.stop_address_tracking()
            self._address_monitor = AddressChangeMonitor(self.address_change_callback)
            log_info("RevEng.AI | Started notification-based address tracking")
            
        except Exception as e:
            log_error(f"RevEng.AI | Error starting address tracking: {str(e)}")

    def stop_address_tracking(self):
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
        try:
            if self._address_monitor:
                self._address_monitor.set_callback(callback)
            if self._timer_monitor:
                self._timer_monitor.set_callback(callback)
            else:
                self.start_address_tracking(callback)
        except Exception as e:
            log_error(f"RevEng.AI | Error setting address tracking callback: {str(e)}")
    
    def address_change_callback(self, context, view, addr, change_type):
        if change_type == "address_changed" and addr is not None:
            log_info(f"RevEng.AI | Address changed to 0x{addr:x} - could trigger AI decompilation here")
            if self.dialog:
                log_info(f"RevEng.AI | Pre-tab setup for address 0x{addr:x}")
                bv = view.getCurrentViewInterface().getData() 
                self.dialog.pre_tab_setup(bv, addr)

    def start_ai_decompiler(self, bv: BinaryView, options: Dict) -> None:
        try:
            if not self.tracking_enabled:
                self.start_address_tracking(self.address_change_callback)
                self.tracking_enabled = True
            
            log_info("RevEng.AI | Starting function searching in portal")
            editor = options.get("editor")
            tab_name = options.get("tab_name")
            function = options.get("function")
            callback = options.get("callback")
            analysis_id = self.config.get_analysis_id(bv)
            if not analysis_id:
                raise Exception("Analysis not found. Please choose one using the 'Attach to existing' feature.")
            function_id = get_function_id_by_addr_util(bv, function.start, self.config)

            with revengai.ApiClient(self.config.api_config) as api_client:
                api_instance = revengai.FunctionsAIDecompilationApi(api_client)
                api_response_status = api_instance.get_ai_decompilation_task_status(function_id)
                log_info(f"RevEng.AI | AI Decompilation task created for function at 0x{function.start:x}")

            poll_status = api_response_status.data.status
            if not poll_status:
                raise Exception("AI Decompilation task not found.")
            
            log_info(f"RevEng.AI | Polling AI decompilation: {poll_status}")

            if poll_status.lower() != "completed" and poll_status.lower() != "failed":
                log_info(f"RevEng.AI | Starting AI Decompilation for function at 0x{function.start:x}")

                if poll_status.lower() == "uninitialised":
                    try:
                        with revengai.ApiClient(self.config.api_config) as api_client:
                            api_instance = revengai.FunctionsAIDecompilationApi(api_client)
                            api_response_status = api_instance.create_ai_decompilation_task(function_id)
                            log_info(f"RevEng.AI | AI Decompilation task created for function at 0x{function.start:x}")
                            if not api_response_status.status:
                                callback(editor, "AI Decompilation failed.")
                                return

                    except Exception as e:
                        log_error(f"RevEng.AI | Error beginning AI decompilation: {str(e)}")
                        callback(editor, "AI Decompilation failed.")
                        return

                log_info("RevEng.AI | AI Decompilation started")
                periodic_checker = AIDecompilerChecker()
                periodic_checker.start_ai_decompiler_checking(function_id, callback, editor, tab_name, self.config)
                self._current_checker = periodic_checker

            if poll_status.lower() == "completed":
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function.start:x} is completed")
                with revengai.ApiClient(self.config.api_config) as api_client:
                    api_instance = revengai.FunctionsAIDecompilationApi(api_client)
                    api_response_status = api_instance.get_ai_decompilation_task_result(function_id, summarise=True, generate_inline_comments=True)

                callback(editor, api_response_status.data.decompilation)

            if poll_status.lower() == "failed":
                log_info(f"RevEng.AI | AI Decompilation for function at 0x{function.start:x} failed")
                callback(editor, "AI Decompilation failed.")

        except Exception as e:
            log_error(f"RevEng.AI | Error in AI decompiler: {str(e)}")
            callback(editor, "AI Decompilation failed.")
            return False, str(e)
