from threading import Timer
from os.path import basename
from typing import Optional
import revengai
from binaryninja import log_info, log_error, BinaryView
from requests.exceptions import RequestException
from PySide6.QtCore import QObject
from reai_toolkit.utils.core.sync import AnalysisSyncService

_IN_PROGRESS_STATUSES = (
    revengai.StatusInput.UPLOADED,
    revengai.StatusInput.QUEUED,
    revengai.StatusInput.PROCESSING,
)


class PeriodicChecker(QObject):
    sync_service: AnalysisSyncService

    def __init__(self, config):
        super().__init__()
        self._current_timer: Optional[Timer] = None
        self.number_of_clicks = 0
        self.config = config
        self.sync_service = AnalysisSyncService(config)

    def stop(self):
        if self._current_timer:
            self._current_timer.cancel()
            self._current_timer = None
            log_info("RevEng.AI | Stopped periodic status check")

    def start_checking(
        self,
        binary_view: BinaryView,
        analysis_id: int,
        binary_id: int,
        callback,
        interval: float = 60,
    ) -> None:
        def _worker(bv: BinaryView, bid: int, aid: int):
            try:
                with self.config.create_api_client() as api_client:
                    api_instance = revengai.AnalysesCoreApi(api_client)
                    api_response = api_instance.get_analysis_status(aid)
                    status = api_response.data.analysis_status
                    log_info(
                        f"RevEng.AI | Current status for analysis [Binary ID: {bid}] [Analysis ID: {aid}]: {status}"
                    )

                if status in _IN_PROGRESS_STATUSES:
                    if bv and bv.file and bv.file.filename:
                        self._current_timer = Timer(
                            interval, _worker, args=(bv, bid, aid)
                        )
                        self._current_timer.start()
                        log_info(
                            f"RevEng.AI | Scheduled next status check for: {basename(bv.file.filename)} [Binary ID: {bid}] [Analysis ID: {aid}]"
                        )
                elif status == revengai.StatusInput.COMPLETE:
                    # Analysis is complete, fetch model_id and invoke callback
                    with self.config.create_api_client() as api_client:
                        api_instance = revengai.AnalysesCoreApi(api_client)
                        analysis_details: revengai.BaseResponseBasic = (
                            api_instance.get_analysis_basic_info(
                                analysis_id=analysis_id
                            )
                        )
                        model_id = analysis_details.data.model_id
                        callback(bid, aid, model_id)

                        bv = self.sync_service.sync_analysis_data(
                            analysis_id=aid, bv=bv
                        )

                        log_info(
                            f"RevEng.AI | Analysis completed with status: {status} for Binary ID: {bid} | Analysis ID: {aid} | Model ID: {model_id}"
                        )
                else:
                    log_error(
                        f"RevEng.AI | Analysis failed with status '{status}' "
                        f"[Binary ID: {bid}] [Analysis ID: {aid}]. "
                        "Check the analysis log in the RevEng.AI portal, then re-run the analysis."
                    )
            except RequestException as ex:
                log_error(
                    f"RevEng.AI | Network error while monitoring analysis [Binary ID: {bid}] [Analysis ID: {aid}]: {ex}"
                )
            except Exception as ex:
                log_error(
                    f"RevEng.AI | Unexpected error while monitoring analysis [Binary ID: {bid}] [Analysis ID: {aid}]: {ex}"
                )

        self.stop()

        self._current_timer = Timer(
            30, _worker, args=(binary_view, binary_id, analysis_id)
        )
        self._current_timer.start()
        log_info(
            f"RevEng.AI | Started periodic status check for: {basename(binary_view.file.filename)} [Binary ID: {binary_id}] [Analysis ID: {analysis_id}]"
        )
