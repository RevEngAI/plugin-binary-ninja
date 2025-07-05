from PySide6.QtCore import QThread, Signal

class ChooseSourceThread(QThread):
    finished = Signal(bool, str) 
    
    def __init__(self, choose_source, bv, chose):
        super().__init__()
        self.choose_source = choose_source
        self.bv = bv
        self.chose = chose
        
    def run(self):
        try:
            success = self.choose_source.choose_source(self.bv, self.chose) # Change to return error message
            if success:
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "")
        except Exception as e:
            self.finished.emit(False, str(e)) 