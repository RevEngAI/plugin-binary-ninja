from threading import Timer
from os.path import basename
from typing import Optional
import revengai
from binaryninja import log_info, log_error, BinaryView
from requests.exceptions import RequestException
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal

class PeriodicChecker(QObject):
    update_text_signal = Signal(object, str)
    
    def __init__(self):
        super().__init__()
        self._current_timer: Optional[Timer] = None
        self.number_of_clicks = 0
        self.update_text_signal.connect(self._update_text_slot)

    def _update_text_slot(self, callback, text):
        """Slot that runs in the main thread to safely update UI"""
        try:
            if hasattr(callback, '__call__'):
                if hasattr(self, '_current_editor'):
                    callback(self._current_editor, text)
        except Exception as ex:
            log_error(f"RevEng.AI | Error updating UI: {str(ex)}")

    def stop(self):
        if self._current_timer:
            self._current_timer.cancel()
            self._current_timer = None
            log_info("RevEng.AI | Stopped periodic status check")
        

    def start_checking(self, binary_view: BinaryView, analysis_id: int, binary_id: int, callback, api_config, interval: float = 60) -> None:
        def _worker(bv: BinaryView, bid: int, aid: int):
            try:
                with revengai.ApiClient(api_config) as api_client:
                    api_instance = revengai.AnalysesCoreApi(api_client)
                    api_response = api_instance.get_analysis_status(aid)   
                    status = api_response.data.analysis_status
                    log_info(f"RevEng.AI | Current status for analysis [Binary ID: {bid}] [Analysis ID: {aid}]: {status}")

                if status in ("Queued", "Processing"):
                    if bv and bv.file and bv.file.filename:
                        self._current_timer = Timer(
                            interval,
                            _worker,
                            args=(bv, bid, aid)
                        )
                        self._current_timer.start()
                        log_info(
                            f"RevEng.AI | Scheduled next status check for: {basename(bv.file.filename)} [Binary ID: {bid}] [Analysis ID: {aid}]"
                        )
                else:

                    # Anaysis is complete, fetch model_id and invoke callback
                    with revengai.ApiClient(api_config) as api_client:
                        api_instance = revengai.AnalysesCoreApi(api_client)
                        analysis_details: revengai.BaseResponseBasic = api_instance.get_analysis_basic_info(
                            analysis_id=analysis_id
                        )
                        model_id = analysis_details.data.model_id
                        callback(bid, aid, model_id)
                        log_info(f"RevEng.AI | Analysis completed with status: {status} for Binary ID: {bid} | Analysis ID: {aid} | Model ID: {model_id}")
            except RequestException as ex:
                log_error(f"RevEng.AI | Error getting binary analysis status: {str(ex)}")
            except Exception as ex:
                log_error(f"RevEng.AI | Unexpected error during status check: {str(ex)}")

        self.stop()

        self._current_timer = Timer(30, _worker, args=(binary_view, binary_id, analysis_id))
        self._current_timer.start()
        log_info(
            f"RevEng.AI | Started periodic status check for: {basename(binary_view.file.filename)} [Binary ID: {binary_id}] [Analysis ID: {analysis_id}]"
        )