import time
from typing import List, Dict, Tuple
from libbs.api import DecompilerInterface
from libbs.artifacts import _art_from_dict, Function
from binaryninja import BinaryView, log_info, log_error
from libbs.decompilers.binja.interface import BinjaInterface
from concurrent.futures import ThreadPoolExecutor, as_completed
from reai_toolkit.utils import rename_function as rename_function_util, apply_data_types as apply_data_types_util
from reait.api import RE_search, RE_nearest_symbols_batch, RE_analyze_functions, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll

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

    def _process_batch(self, function_ids: List[int], id_to_addr: Dict[int, int], bv: BinaryView, debug_symbols: bool, data_types: bool, deci: DecompilerInterface = None, chunk_index: int = 0) -> Tuple[int, List[str]]:
        try:
            functions_by_distance = RE_nearest_symbols_batch(
                function_ids=function_ids,
                distance=self.auto_unstrip_distance,
                debug_enabled=debug_symbols,
                nns=1
            ).json()["function_matches"]

            functions = []
            for function in functions_by_distance:
                functions.append({"function_id": function['origin_function_id'], "function_name": function['nearest_neighbor_function_name']})
            #log_info(f"RevEng.AI | Functions by distance: {functions}")
            functions_by_score = RE_name_score(functions).json()["data"]
            #log_info(f"RevEng.AI | Functions by score: {functions_by_score}")
            renamed_count = 0
            errors = []
            to_datatypes = []
            for result in functions_by_distance:
                try:
                    func_id = result['origin_function_id']
                    func_addr = id_to_addr.get(func_id)
                    if not func_addr:
                        continue

                    new_name = result['nearest_neighbor_function_name']
                    if not new_name or new_name.startswith(("sub_", "FUN_")):
                        continue
                    
                    new_name_mangled = result['nearest_neighbor_function_name_mangled']
                    if not new_name_mangled or new_name_mangled.startswith(("sub_", "FUN_")):
                        continue
                    
                    for function in functions_by_score:
                        if function['function_id'] == func_id:
                           if function['box_plot']["average"] < 90:
                                log_info(f"RevEng.AI | Function {function['function_id']} has a score of {function['box_plot']['average']:.2f} for name {new_name_mangled}, skipping")
                                break
                           else:
                                log_info(f"RevEng.AI | Function {function['function_id']} has a score of {function['box_plot']['average']:.2f} for name {new_name_mangled}, renaming")
                                if data_types:                                  
                                    to_datatypes.append(result)
                                if rename_function_util(bv, func_addr, new_name_mangled):
                                    renamed_count += 1
                                break
                           
                    if to_datatypes:
                        self.resolve_data_types(to_datatypes, id_to_addr, deci, chunk_index)

                except Exception as e:
                    log_error(f"RevEng.AI | Error processing function {result['origin_function_id']}: {str(e)}")
                    errors.append(str(e))

            return renamed_count, errors

        except Exception as e:
            return 0, [str(e)]

    def auto_unstrip(self, bv: BinaryView, options: Dict): 
        try:    
            log_info("RevEng.AI | Auto Unstripping binary")

            debug_symbols = options.get("debug_symbols", True)
            data_types = options.get("data_types", False)

            self.base_addr = bv.image_base
            self.path = bv.file.filename
            binary_id = self.config.get_binary_id(bv)
            log_info(f"RevEng.AI | Path: {self.path}")
            log_info(f"RevEng.AI | Binary ID: {binary_id}")

            results = RE_search(fpath=self.path).json()["query_results"]
            log_info(f"RevEng.AI | Search Results: {results}")

            if not len(results):
                raise Exception("Binary not found in RevEng.AI, try uploading again.")
            
            analyzed_functions = RE_analyze_functions(self.path, binary_id).json()["functions"]
            function_ids = [func["function_id"] for func in analyzed_functions]

            id_to_addr = {
                func["function_id"]: func["function_vaddr"] + self.base_addr
                for func in analyzed_functions
            }

            chunk_size = 50
            chunks = [function_ids[i:i + chunk_size] for i in range(0, len(function_ids), chunk_size)]
            
            log_info(f"RevEng.AI | Processing {len(function_ids)} functions in {len(chunks)} chunks of size {chunk_size}")

            total_renamed = 0
            all_errors = []
            deci = None
            if data_types:
                deci = BinjaInterface(bv)

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(self._process_batch, chunk, id_to_addr, bv, debug_symbols, data_types, deci, i): i 
                    for i, chunk in enumerate(chunks)
                }

                for future in as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:
                        renamed_count, errors = future.result()
                        total_renamed += renamed_count
                        all_errors.extend(errors)
                        log_info(f"RevEng.AI | Chunk {chunk_index} completed: renamed {renamed_count} functions")
                    except Exception as e:
                        log_error(f"RevEng.AI | Error processing chunk {chunk_index}: {str(e)}")

            if total_renamed > 0:
                message = f"Successfully renamed {total_renamed} functions!"
            else:
                message = "After analyzing the binary, no functions were found to be renamed."
            
            """
            if all_errors:
                message += f"\nEncountered {len(all_errors)} errors during processing."
            """
            
            log_info(f"RevEng.AI | {message}")
            return True, message

        except Exception as e:
            log_error(f"RevEng.AI | Error: {str(e)}")
            return False, str(e)
