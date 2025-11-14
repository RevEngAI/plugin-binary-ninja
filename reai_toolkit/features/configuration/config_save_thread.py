from PySide6.QtCore import QThread, Signal

class ConfigSaveThread(QThread):
    finished = Signal(bool, str)
    
    def __init__(self, config, api_key, host):
        super().__init__()
        self.config = config
        self.api_key = api_key
        self.host = host
        
    def run(self):
        try:
            self.config.api_key = self.api_key
            self.config.host = self.host
            success = self.config.save_config()
            
            if not success:
                self.finished.emit(False, "API key not valid or host not reachable.")
            else:
                self.finished.emit(True, "")
                
        except Exception as e:
            self.finished.emit(False, str(e)) 