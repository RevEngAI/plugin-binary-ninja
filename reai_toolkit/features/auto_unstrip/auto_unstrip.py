import time
import revengai
from typing import List, Dict, Tuple
from libbs.api import DecompilerInterface
from libbs.artifacts import _art_from_dict, Function
from binaryninja import BinaryView, log_info, log_error
from libbs.decompilers.binja.interface import BinjaInterface
from concurrent.futures import ThreadPoolExecutor, as_completed
from reai_toolkit.utils import rename_function as rename_function_util, apply_data_types as apply_data_types_util, get_function_by_addr as get_function_by_addr_util
from revengai import AutoUnstripRequest

class AutoUnstrip:
    def __init__(self, config):
        self.config = config
        self.auto_unstrip_distance = 0.09999999999999998
        self.base_addr = None
        self.path = None
        self.max_workers = 4 

    def resolve_data_types(self, to_datatypes: List[Dict], id_to_addr: Dict[int, int], deci: DecompilerInterface, chunk_index: int) -> None:
        try:
            function_ids = set([result['nearest_neighbor_id'] for result in to_datatypes])
            log_info(f"RevEng.AI | Resolving data types for {len(function_ids)} functions")
            RE_functions_data_types(function_ids=list(function_ids))
            
            items = []
            while True:
                response = RE_functions_data_types_poll(    
                    function_ids=list(function_ids),
                ).json()
                data = response.get("data", {})
                items = data.get("items", [])
                pending_count = sum(1 for item in items if item.get("status") == "pending")
                log_info(f"RevEng.AI | [Chunk {chunk_index}] {pending_count} items still pending...")
                if not pending_count:
                    break
                time.sleep(3)

            for item in items:
                log_info(f"RevEng.AI | Item: {item['function_id']}")
                if item['status'] != "completed":
                    continue
                for result in to_datatypes:
                    if result['nearest_neighbor_id'] == item['function_id']:

                        
                        signature = "N/A"
                        item2 = item.get("data_types", {})
                        func_types = item2.get("func_types", None)
                        func_deps = item2.get("func_deps", [])
                        log_info(f"RevEng.AI | Func types: {func_types}")
                        if func_types is not None:
                            fnc: Function = _art_from_dict(func_types)
                            if fnc.name is None:
                                log_info(f"Function {item['function_id']} has no name, skipping signature application.")
                                continue

                            addr = id_to_addr.get(result['origin_function_id'])
                            if not addr:
                                continue
                            log_info(f"RevEng.AI | Applying signature for {fnc.name} at 0x{addr:x}")
                            signature_data = {"deps": func_deps, "function": fnc}
                            apply_data_types_util(addr, signature_data, deci)
                            log_info(f"RevEng.AI | Successfully applied signature for {fnc.name} at 0x{addr:x}")
                            break
                        break

        except Exception as e:
            log_error(f"RevEng.AI | Error resolving data types: {str(e)}")


    def rename_functions(self, bv: BinaryView, options: List[Dict]):
        try:
            renamed_count = 0
            for option in options:
                if rename_function_util(bv, option['virtual_address'], option['suggested_name']):
                    renamed_count += 1
            return True, f"Successfully renamed {renamed_count} functions"
        except Exception as e:
            log_error(f"RevEng.AI | Error renaming functions: {str(e)}")
            return False, str(e)

    def auto_unstrip(self, bv: BinaryView): 
        try:    
            log_info("RevEng.AI | Auto Unstripping binary")

            analysis_id = self.config.get_analysis_id(bv)
            auto_unstrip_request = revengai.AutoUnstripRequest()
            matches = []
            results = []

            with revengai.ApiClient(self.config.api_config) as api_client:
                api_instance = revengai.FunctionsCoreApi(api_client)
                api_response = api_instance.auto_unstrip(analysis_id, auto_unstrip_request)
                
                if api_response.status.lower() == "error":
                    raise Exception(api_response.error)
                elif api_response.status.lower() != "completed":
                    while True:
                        time.sleep(3)
                        api_response = api_instance.auto_unstrip(analysis_id, auto_unstrip_request)
                        if api_response.status.lower() == "completed":
                            break
                        if api_response.status.lower() == "error":
                            raise Exception(api_response.error)

                if api_response.status.lower() == "completed":
                    matches = api_response.matches
                else:
                    raise Exception(api_response.error)
            for match in matches:
                try:
                    function = get_function_by_addr_util(bv, match.function_vaddr)
                    results.append({"virtual_address": match.function_vaddr, "current_name": function.name, "suggested_name": match.suggested_demangled_name})
                except Exception as e:
                    log_error(f"RevEng.AI | Error getting function by address {match.function_vaddr}: {str(e)}")
                    results.append({"virtual_address": match.function_vaddr, "current_name": "N/A", "suggested_name": match.suggested_demangled_name})

            return True, results

        except Exception as e:
            log_error(f"RevEng.AI | Error: {str(e)}")
            return False, str(e)
