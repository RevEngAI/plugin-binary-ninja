from PySide6.QtCore import QThread, Signal
from binaryninja import log_error

class AnalysisLoadThread(QThread):
    finished = Signal(list) 
    error = Signal(str)
    
    def __init__(self, choose_source, bv):
        super().__init__()
        self.choose_source = choose_source
        self.bv = bv
        
    def run(self):
        try:
            analysis = self.choose_source.get_analysis(self.bv)
            if not len(analysis):
                raise Exception("No analysis found, try processing the binary again.")
            self.finished.emit(analysis)
        except Exception as e:
            log_error(f"RevEng.AI | Failed to load analysis: {str(e)}")
            self.error.emit(str(e)) 