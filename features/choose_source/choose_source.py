from binaryninja import BinaryView, log_info, log_error, Symbol, SymbolType
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import math

class ChooseSource:
    def __init__(self, config):
        self.config = config

    def choose_source(self, bv: BinaryView, chose: str): 
        try:
            log_info(f"RevEng.AI | Chose: {chose}")
            binary_id = chose.split("ID: ")[1].split(" -")[0]
            self.config.binary_id = binary_id
            log_info(f"RevEng.AI | Binary ID: {self.config.binary_id}")
            # TODO: implement array like to store binary id and binaryhash and filesize
            return True
        except Exception as e:
            log_error(f"RevEng.AI | Failed to choose source: {str(e)}")
            return False

    def get_analysis(self, bv: BinaryView):
        try:
            self.base_addr = bv.image_base
            self.path = bv.file.filename
            log_info(f"RevEng.AI | Path: {self.path}")
            log_info(f"RevEng.AI | Binary ID: {self.config.binary_id}")

            results = RE_search(fpath=self.path).json()["query_results"]

            if not len(results):
                raise Exception("Binary not found in RevEng.AI, try processing the binary again.")
            
            options = []
            for result in results:
                option = f"Name: {result['binary_name'][:10]}{'...' if len(result['binary_name']) > 10 else ''} - ID: {result['binary_id']} - Model: {result['model_name']} - Created at: {result['creation'].split('T')[0]} {result['creation'].split('T')[1].split('.')[0]}"
                options.append(option)
                log_info(f"RevEng.AI | Analysis: {option}")
                # TODO: put the current binary id first in the list

            return options
        except Exception as e:
            log_error(f"RevEng.AI | Failed to get analysis: {str(e)}")
            return []