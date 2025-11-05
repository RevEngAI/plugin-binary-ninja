import revengai
from reai_toolkit.utils import get_sha256
from binaryninja import BinaryView, log_info, log_error

class ChooseSource:
    def __init__(self, config):
        self.config = config

    def choose_source(self, bv: BinaryView, chose: str): 
        try:
            log_info(f"RevEng.AI | Item: {chose}")
            new_binary_id = int(chose.split("Binary ID: ")[1].split(" -")[0])
            new_analysis_id = int(chose.split("Analysis ID: ")[1].split(" -")[0])
            analysis_id = self.config.get_analysis_id(bv)
            binary_id = self.config.get_binary_id(bv)
            if binary_id == new_binary_id and analysis_id == new_analysis_id:
                log_info("RevEng.AI | Binary ID and Analysis ID are already set to the chosen one.")
                return True, "Binary ID is already set to the chosen one."
            
            log_info(f"RevEng.AI | Changing Binary ID: {binary_id} to {new_binary_id}")
            log_info(f"RevEng.AI | Changing Analysis ID: {analysis_id} to {new_analysis_id}")
            self.config.set_current_info(new_binary_id, new_analysis_id)

            return True, "Binary ID changed successfully."
        except Exception as e:
            log_error(f"RevEng.AI | Failed to choose source: {str(e)}")
            return False, str(e)

    def get_analysis(self, bv: BinaryView):
        try:
            log_info(f"RevEng.AI | Path: {bv.file.filename}")
            binary_id = self.config.get_binary_id(bv)
            log_info(f"RevEng.AI | Current Binary ID: {binary_id}")
            analysis_id = self.config.get_analysis_id(bv)
            log_info(f"RevEng.AI | Current Analysis ID: {analysis_id}")
            
            sha256 = get_sha256(bv.file.filename)

            with revengai.ApiClient(self.config.api_config) as api_client:
                api_instance = revengai.SearchApi(api_client)
                api_response = api_instance.search_binaries(partial_sha256 = sha256, user_files_only = True)
                results = api_response.data.results
            if not len(results):
                raise Exception("Binary not found in RevEng.AI, try processing the binary again.")
            
            options = []
            for result in results:
                option = f"Name: {result.binary_name[:10]}{'...' if len(result.binary_name) > 10 else ''} - Binary ID: {result.binary_id} - Analysis ID: {result.analysis_id} - Model: {result.model_name} - Created at: {result.created_at.strftime('%m/%d/%Y %H:%M')}"
                log_info(f"RevEng.AI | Analysis: {option}")
                if result.binary_id == binary_id and result.analysis_id == analysis_id:
                    options.insert(0, option)
                else:
                    options.append(option)

            return True, options
        except Exception as e:
            log_error(f"RevEng.AI | Failed to get analysis: {str(e)}")
            return False, str(e)