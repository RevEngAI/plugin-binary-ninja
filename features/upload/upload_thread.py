from PySide6.QtCore import QThread, Signal

class UploadBinaryThread(QThread):
    finished = Signal(bool, str) 
    
    def __init__(self, uploader, bv, options):
        super().__init__()
        self.uploader = uploader
        self.bv = bv
        self.options = options
        
    def run(self):
        try:
            success = self.uploader.upload_binary(self.bv, self.options) # Change to return error message
            if success:
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "")
        except Exception as e:
            self.finished.emit(False, str(e)) 