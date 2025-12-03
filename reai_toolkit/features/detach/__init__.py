from reai_toolkit.utils import BaseAuthFeature
from binaryninja import PluginCommand, log_info, BinaryView
from PySide6.QtWidgets import QMessageBox

class DetachAnalysisFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)
        log_info("RevEng.AI | DetachAnalysis Feature initialized")

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Analysis\\\u200b\u200b\u200bDetach Analysis",
            "Detach from the current RevEng.AI analysis",
            self.verify_detach,
            self.is_valid
        )
        log_info("RevEng.AI | DetachAnalysis Feature registered")

    def verify_detach(self, bv: BinaryView):
        log_info("RevEng.AI | Requesting detach confirmation")
        
        reply = QMessageBox.question(
            None,
            "RevEng.AI - Detach Analysis",
            "Are you sure you want to detach from the current RevEng.AI analysis?\n\n"
            "This will disconnect this binary from its analysis on the RevEng.AI platform. "
            "You can reconnect later by choosing a source again.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            log_info("RevEng.AI | User confirmed detach")
            self.config.reset_analysis_data(bv)
            
            QMessageBox.information(
                None,
                "RevEng.AI - Analysis Detached",
                "Successfully detached from the RevEng.AI analysis.\n\n"
                "You can process a new binary or choose a different source.",
                QMessageBox.Ok
            )
        else:
            log_info("RevEng.AI | User cancelled detach")

    def is_valid(self, bv: BinaryView):
        return self.config.is_configured == True and self.config.analysis_id is not None 