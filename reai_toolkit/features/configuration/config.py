import json
import revengai
from reai_toolkit.utils import get_sha256
from binaryninja import Settings, log_info, log_error, BinaryView


class Config:
    def __init__(self):
        self.settings = Settings()
        self.api_key = ""
        self.host = ""
        self.sha256 = ""
        self.api_config = None
        self.is_configured = False
        self._load_config()
  

    def _load_config(self):
        settings = Settings()
        settings.register_group("revengai", "RevEng.AI")
        log_info(f"RevEng.AI | Registering settings")
        log_info(settings.register_setting("revengai.host", 
            '{"title" : "Host URL",\
            "type" : "string",\
            "default" : "https://api.reveng.ai",\
            "description" : "RevEng.AI Host URL"}'))
        log_info(settings.register_setting("revengai.api_key", 
            '{"title" : "API Key",\
            "type" : "string",\
            "default" : "",\
            "description" : "API Key"}'))
        log_info(settings.register_setting("revengai.all_analyses", 
            '{"title" : "All Analyses",\
            "type" : "object",\
            "description" : "All Analyses"}'))
            
        self.host = settings.get_string("revengai.host", None)
        self.api_key = settings.get_string("revengai.api_key", None)

        self.init_api_config()
        #re_conf["user_agent"] = "RevEng.AI BinaryNinja Plugin"
        

    def save_config(self) -> bool:
        try:
            log_info(f"RevEng.AI | Testing configuration: {self.host} {self.api_key[:4]}...")
            
            if not self.check_auth():
                raise Exception(f"RevEng.AI | Authentication failed.")
            
            self.is_configured = True

            settings = Settings()
            settings.set_string("revengai.host", self.host)
            settings.set_string("revengai.api_key", self.api_key)

            return True
        
        except Exception as e:
            log_info(f"RevEng.AI | Failed to save API key: {str(e)}")
            self.is_configured = False
            return False

    
    def init_api_config(self):
        try:
            self.api_config = revengai.Configuration(api_key={'APIKey': self.api_key}, host=self.host)
        except Exception as e:
            log_error(f"RevEng.AI | Failed to initialize API client: {str(e)}")
        
        
    def clear_config(self):
        self.api_key = ""
        self.host = ""
        self.is_configured = False
        self.save_config() 


    def check_auth(self):
        try:
            self.init_api_config()
            with revengai.ApiClient(self.api_config) as api_client:
                api_instance = revengai.AuthenticationUsersApi(api_client)
                api_response = api_instance.get_requester_user_info()
                log_info(f"RevEng.AI | Welcome {api_response.data.username}!")
            return True
        except Exception as e: 
            log_error(f"RevEng.AI | Failed to check authentication: {str(e)}")
            return False
        
        
    def get_all_analyses(self):
        settings = Settings()
        all_analyses = settings.get_json("revengai.all_analyses", None)
        if all_analyses == "null":
            return {}
        return json.loads(all_analyses)
    

    def set_current_info(self, binary_id, analysis_id):
        binary_id = int(binary_id)
        self.binary_id = binary_id
        self.analysis_id = analysis_id

        all_analyses = self.get_all_analyses()
        all_analyses[self.sha256] = {"binary_id": binary_id, "analysis_id": analysis_id}
        settings = Settings()
        
        settings.set_json("revengai.all_analyses", json.dumps(all_analyses))
        log_info(f"RevEng.AI | Updated analysis for SHA256: {self.sha256[:8]}... with binary_id: {binary_id} and analysis_id: {analysis_id}")


    def init_config(self, bv: BinaryView):
        try:
            if not self.check_auth():
                self.is_configured = False
                raise Exception("RevEng.AI | Authentication failed.")
            
            self.is_configured = True

            self.sha256 = get_sha256(bv.file.filename)

            log_info(f"RevEng.AI | SHA256: {self.sha256}")

            all_analyses = self.get_all_analyses()
            if self.sha256 in all_analyses:
                log_info(f"RevEng.AI | Binary found in saved configurations, binary_id: {all_analyses[self.sha256]['binary_id']} and analysis_id: {all_analyses[self.sha256]['analysis_id']}")
                self.binary_id = all_analyses[self.sha256]["binary_id"]
                self.analysis_id = all_analyses[self.sha256]["analysis_id"]
            else:
                log_info(f"RevEng.AI | Binary not found in saved configurations, searching in RevEng.AI...")
                with revengai.ApiClient(self.api_config) as api_client:
                    api_instance = revengai.SearchApi(api_client)
                    api_response = api_instance.search_binaries(partial_sha256 = self.sha256, user_files_only = True)
                if not len(api_response.data.results):
                    raise Exception("Binary not found in RevEng.AI, try processing the binary again.")
                else:
                    self.binary_id = api_response.data.results[0].binary_id
                    self.analysis_id = api_response.data.results[0].analysis_id
                    log_info(f"RevEng.AI | Binary found in RevEng.AI, binary_id: {self.binary_id}")
                    self.set_current_info(self.binary_id, self.analysis_id)
            
            return True, ""

        except Exception as e:
            log_error(f"RevEng.AI | Failed to initialize configuration: {str(e)}")
            return False, str(e)


    def get_binary_id(self, bv: BinaryView):
        self.sha256 = get_sha256(bv.file.filename)
        all_analyses = self.get_all_analyses()
        if self.sha256 in all_analyses:
            return all_analyses[self.sha256]["binary_id"]
        else:
            return 0
    
    def get_analysis_id(self, bv: BinaryView):
        
        self.sha256 = get_sha256(bv.file.filename)
        all_analyses = self.get_all_analyses()
        if self.sha256 in all_analyses:
            return all_analyses[self.sha256]["analysis_id"]
        else:
            return 0