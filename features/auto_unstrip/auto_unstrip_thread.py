from PySide6.QtCore import QThread, Signal

class AutoUnstripThread(QThread):
    finished = Signal(bool, str)  # Signal for success/failure and error message
    
    def __init__(self, auto_unstrip, bv):
        super().__init__()
        self.auto_unstrip = auto_unstrip
        self.bv = bv
        
    def run(self):
        try:
            success, message = self.auto_unstrip.auto_unstrip(self.bv)
            if success:
                self.finished.emit(True, message)
            else:
                self.finished.emit(False, message)
        except Exception as e:
            self.finished.emit(False, str(e)) 