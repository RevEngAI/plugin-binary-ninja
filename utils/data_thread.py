from PySide6.QtCore import QThread, Signal
from binaryninja import log_info, BinaryView

class DataThread(QThread):
    finished = Signal(bool, object) 
    
    def __init__(self, callback_function, bv: BinaryView, args = None):
        super().__init__()
        self.callback_function = callback_function
        self.bv = bv
        self.args = args
        log_info(f"RevEng.AI | Data thread initialized")

    def run(self):
        try:
            if self.args is None:
                success, content = self.callback_function(self.bv)
            else:
                success, content = self.callback_function(self.bv, self.args)

            if success:
                log_info(f"RevEng.AI | Data thread finished with success")
                log_info(f"RevEng.AI | Content: {content}")
                self.finished.emit(True, content)
            else:
                self.finished.emit(False, content)
        except Exception as e:
            self.finished.emit(False, str(e)) 