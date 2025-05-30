from binaryninja import BinaryView, log_info, log_error
from reait.api import RE_models

class BinaryUploader:
    def __init__(self, config):
        self.config = config

    
    def get_models(self):
        try:
            models = RE_models().json()
            return set([model["model_name"] for model in models["models"]])
        except Exception as e:
            log_error(f"Failed to get models: {str(e)}")
            return set()
                

    def upload_binary(self, bv: BinaryView, options: dict):
        try:
            
            # TODO: Implement actual upload logic here
            # This will involve:
            # 1. Getting the binary data from bv
            # 2. Use the RE_upload_binary function to upload the binary
            # 3. Handling the response
            
            log_info(f"Binary {bv.file.filename} uploaded successfully with options: {options}")
            return True
            
        except Exception as e:
            log_error(f"Failed to upload binary: {str(e)}")
            return False 