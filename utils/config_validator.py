from PySide6.QtWidgets import QMessageBox
from binaryninja import log_error

def validate_config(config):
    if not config.is_configured():
        log_error("RevEng.AI configuration is missing or incomplete")
        QMessageBox.warning(
            None,
            "RevEng.AI Configuration Required",
            "Please configure your RevEng.AI API key and host before uploading.\n\n"
            "You can do this through:\nRevEng.AI > Configure",
            QMessageBox.Ok
        )
        return False
        
    return True 