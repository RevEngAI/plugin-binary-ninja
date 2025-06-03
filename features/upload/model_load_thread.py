from PySide6.QtCore import QThread, Signal
from binaryninja import log_error

class ModelLoadThread(QThread):
    finished = Signal(list)  # Signal emitting the loaded models
    error = Signal(str)     # Signal for error handling
    
    def __init__(self, uploader, bv):
        super().__init__()
        self.uploader = uploader
        self.bv = bv
        
    def run(self):
        try:
            models = self.uploader.get_models(self.bv)
            self.finished.emit(models)
        except Exception as e:
            log_error(f"RevEng.AI | Failed to load models: {str(e)}")
            self.error.emit(str(e)) 