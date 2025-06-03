from binaryninja import Settings, log_info
from reait.api import re_conf, RE_authentication

class Config:
    def __init__(self):
        self.settings = Settings()
        self.api_key = ""
        self.host = ""
        self.current_analysis = None
        self.is_configured = None
        self.binary_id = None
        self.analysis_id = None
        self._load_config()
        

    def _load_config(self):
        settings = Settings()
        settings.register_group("revengai", "RevEng.AI")
        settings.register_setting("revengai.host", 
            '{"title" : "Host URL",\
            "type" : "string",\
            "default" : "https://api.reveng.ai",\
            "description" : "RevEng.AI Host URL"}')
        settings.register_setting("revengai.api_key", 
            '{"title" : "API Key",\
            "type" : "string",\
            "default" : "",\
            "description" : "API Key"}')
        settings.register_setting("revengai.current_analysis", 
            '{"title" : "Current Analysis ID",\
            "type" : "string",\
            "default" : "",\
            "description" : "Current Analysis ID"}')
        settings.register_setting("revengai.is_configured", 
            '{"title" : "Is Configured",\
            "type" : "string",\
            "default" : "False",\
            "description" : "Configuration Status"}')
        settings.register_setting("revengai.binary_id", 
            '{"title" : "Binary ID",\
            "type" : "string",\
            "default" : "",\
            "description" : "Current Binary ID"}')
        settings.register_setting("revengai.analysis_id", 
            '{"title" : "Analysis ID",\
            "type" : "string",\
            "default" : "",\
            "description" : "Current Analysis ID"}')
            
        self.host = settings.get_string("revengai.host", None)
        self.api_key = settings.get_string("revengai.api_key", None)
        self.current_analysis = settings.get_string("revengai.current_analysis", None)
        self.is_configured = settings.get_string("revengai.is_configured", None)
        self.binary_id = settings.get_integer("revengai.binary_id", None)
        self.analysis_id = settings.get_integer("revengai.analysis_id", None)

        re_conf["apikey"] = self.api_key
        re_conf["host"] = self.host
        

    def save_config(self) -> bool:
        try:
            log_info(f"RevEng.AI | Testing configuration: {self.host} {self.api_key[:4]}...")
            re_conf["apikey"] = self.api_key
            re_conf["host"] = self.host
            RE_authentication()
            log_info("RevEng.AI | Authentication successful!")
            self.is_configured = "True"

            settings = Settings()
            settings.set_string("revengai.host", self.host)
            settings.set_string("revengai.api_key", self.api_key)
            settings.set_string("revengai.is_configured", self.is_configured)
    
            return True
        
        except Exception as e:
            log_info(f"RevEng.AI | Failed to save API key: {str(e)}")
            return False
        
        
    def clear_config(self):
        self.api_key = ""
        self.host = ""
        self.current_analysis = None
        self.is_configured = False
        self.save_config() 

    def set_binary_id(self, binary_id: str):
        """Set the binary ID and store it in settings."""
        self.binary_id = binary_id
        settings = Settings()
        settings.set_integer("revengai.binary_id", self.binary_id)
        return

    def set_analysis_id(self, analysis_id: str):
        """Set the analysis ID and store it in settings."""
        self.analysis_id = analysis_id
        settings = Settings()
        settings.set_integer("revengai.analysis_id", self.analysis_id)
        return
