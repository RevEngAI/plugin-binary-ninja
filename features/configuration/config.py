from binaryninja import Settings, log_info
from reait.api import re_conf, RE_authentication

class Config:
    def __init__(self):
        self.settings = Settings()
        self.api_key = ""
        self.host = ""
        self.current_analysis = None
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
            
        self.host = settings.get_string("revengai.host", None)
        self.api_key = settings.get_string("revengai.api_key", None)
        self.current_analysis = settings.get_string("revengai.current_analysis", None)

        re_conf["apikey"] = self.api_key
        re_conf["host"] = self.host
        

    def save_config(self) -> bool:
        log_info(f"Saving configuration: {self.host} {self.api_key[:4]}...")
        if self.current_analysis:
            settings.set_string("revengai.current_analysis", self.current_analysis)
        
        try:
            re_conf["apikey"] = self.api_key
            re_conf["host"] = self.host
            log_info(f"Saving configuration: {re_conf['apikey']} {re_conf['host']}")
            RE_authentication()
            log_info(f"Authentication successful")
            settings = Settings()
            settings.set_string("revengai.host", self.host)
            settings.set_string("revengai.api_key", self.api_key)
            return True
        
        except Exception as e:
            log_info(f"Failed to save API key: {str(e)}")
            return False
        
        
    def clear_config(self):
        self.api_key = ""
        self.host = ""
        self.current_analysis = None
        self.save_config() 


    def is_configured(self):
        return bool(self.api_key and self.host) 