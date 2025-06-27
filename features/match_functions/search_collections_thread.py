from PySide6.QtCore import QThread, Signal
from binaryninja import log_info, BinaryView

class SearchCollectionsThread(QThread):
    finished = Signal(bool, str)  # Signal for success/failure and error message
    
    def __init__(self, match_functions, bv: BinaryView, search_term):
        super().__init__()
        self.match_functions = match_functions
        self.bv = bv
        self.search_term = search_term
        log_info(f"RevEng.AI | Search term: {search_term}")

    def run(self):
        try:
            success, message = self.match_functions.search_collections(self.bv, self.search_term)
            if success:
                self.finished.emit(True, message)
            else:
                self.finished.emit(False, message)
        except Exception as e:
            self.finished.emit(False, str(e)) 