from reait.api import RE_search
from binaryninja import BinaryView, log_info, log_error

class ChooseSource:
    def __init__(self, config):
        self.config = config

    def choose_source(self, bv: BinaryView, chose: str): 
        try:
            log_info(f"RevEng.AI | Chose: {chose}")
            new_binary_id = int(chose.split("ID: ")[1].split(" -")[0])
            binary_id = self.config.get_binary_id(bv)
            if binary_id == new_binary_id:
                log_info("RevEng.AI | Binary ID is already set to the chosen one.")
                return True, "Binary ID is already set to the chosen one."
            
            log_info(f"RevEng.AI | Changing Binary ID: {binary_id} to {new_binary_id}")
            self.config.set_current_info(new_binary_id)

            return True, "Binary ID changed successfully."
        except Exception as e:
            log_error(f"RevEng.AI | Failed to choose source: {str(e)}")
            return False, str(e)

    def get_analysis(self, bv: BinaryView):
        try:
            log_info(f"RevEng.AI | Path: {bv.file.filename}")
            binary_id = self.config.get_binary_id(bv)
            log_info(f"RevEng.AI | Current Binary ID: {binary_id}")
            

            results = RE_search(fpath=bv.file.filename).json()["query_results"]

            if not len(results):
                raise Exception("Binary not found in RevEng.AI, try processing the binary again.")
            
            options = []
            for result in results:
                option = f"Name: {result['binary_name'][:10]}{'...' if len(result['binary_name']) > 10 else ''} - ID: {result['binary_id']} - Model: {result['model_name']} - Created at: {result['creation'].split('T')[0]} {result['creation'].split('T')[1].split('.')[0]}"
                log_info(f"RevEng.AI | Analysis: {option}")
                if result['binary_id'] == binary_id:
                    options.insert(0, option)
                else:
                    options.append(option)

            return True, options
        except Exception as e:
            log_error(f"RevEng.AI | Failed to get analysis: {str(e)}")
            return False, str(e)