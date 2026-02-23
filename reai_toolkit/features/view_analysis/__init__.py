from reai_toolkit.utils import BaseAuthFeature
from binaryninja import PluginCommand, log_info, BinaryView
from binaryninja.interaction import InteractionHandler

class ViewAnalysisFeature(BaseAuthFeature):
    def __init__(self, config=None):
        super().__init__(config)

    def register(self):
        PluginCommand.register(
            "RevEng.AI\\Analysis\\\u200b\u200bView in portal",
            "View the current analysis in the RevEng.AI portal",
            self.open_analysis,
            self.is_valid
        )

    def open_analysis(self, bv: BinaryView):
        url = f"{self.config.portal_url}/analyses/{self.config.analysis_id}"
        
        if url:
            log_info(f"RevEng.AI | Opening analysis in browser: {url}")
            InteractionHandler().open_url(url)
        else:
            log_info("RevEng.AI | No URL configured for viewing analysis")

    def is_valid(self, bv: BinaryView):
        return self.config.is_configured == True and self.config.analysis_id is not None

