from PySide6.QtCore import QThread, Signal

class UploadBinaryThread(QThread):
    finished = Signal(bool, str)  # Signal for success/failure and error message
    
    def __init__(self, uploader, bv, options):
        super().__init__()
        self.uploader = uploader
        self.bv = bv
        self.options = options
        
    def run(self):
        try:
            success = self.uploader.upload_binary(self.bv, self.options)
            if success:
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "Duplicate binary or host not reachable.")
        except Exception as e:
            self.finished.emit(False, str(e)) 