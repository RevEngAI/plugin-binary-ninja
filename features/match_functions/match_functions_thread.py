from PySide6.QtCore import QThread, Signal

class MatchFunctionsThread(QThread):
    finished = Signal(bool, object)  # Signal for success/failure and data (matches or error message)
    
    def __init__(self, match_functions, bv, distance_threshold=0.1, max_matches=10):
        super().__init__()
        self.match_functions = match_functions
        self.bv = bv
        self.distance_threshold = distance_threshold
        self.max_matches = max_matches
        
    def run(self):
        try:
            matches = self.match_functions.match_functions(
                self.bv, 
                self.distance_threshold, 
                self.max_matches
            )
            self.finished.emit(True, matches)
        except Exception as e:
            self.finished.emit(False, str(e)) 