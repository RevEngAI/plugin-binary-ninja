from threading import Timer
from os.path import basename
from typing import Optional
from binaryninja import log_info, log_error, BinaryView
from requests.exceptions import RequestException
from reait.api import RE_status

class PeriodicChecker:
    def __init__(self):
        self._current_timer: Optional[Timer] = None

    def stop(self):
        """Stop the current periodic check if running"""
        if self._current_timer:
            self._current_timer.cancel()
            self._current_timer = None
            log_info("RevEng.AI | Stopped periodic status check")

    def start_checking(self, binary_view: BinaryView, binary_id: int, interval: float = 60) -> None:
        """
        Start periodic checking of binary analysis status.
        
        Args:
            binary_view (BinaryView): The current binary view
            binary_id (int): The binary ID to check status for
            interval (float): Check interval in seconds (default: 60)
        """
        def _worker(bv: BinaryView, bid: int):
            try:
                # Get status from API
                response = RE_status(bv.file.filename, bid)
                if response.status_code != 200:
                    log_error(f"RevEng.AI | Error getting status: {response.status_code}")
                    return

                status = response.json().get("status")
                log_info(f"RevEng.AI | Current status for binary {bid}: {status}")

                # Continue checking if still processing
                if status in ("Queued", "Processing"):
                    # Only continue if we're still analyzing the same binary
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
                    log_info(f"RevEng.AI | Analysis completed with status: {status}")

            except RequestException as ex:
                log_error(f"RevEng.AI | Error getting binary analysis status: {str(ex)}")
            except Exception as ex:
                log_error(f"RevEng.AI | Unexpected error during status check: {str(ex)}")

        # Stop any existing check
        self.stop()

        # Start initial check
        self._current_timer = Timer(30, _worker, args=(binary_view, binary_id))
        self._current_timer.start()
        log_info(
            f"RevEng.AI | Started periodic status check for: {basename(binary_view.file.filename)} [{binary_id}]"
        )

# Global instance
checker = PeriodicChecker() 