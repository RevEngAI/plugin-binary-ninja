from binaryninja import BinaryView, log_info, log_error, Symbol, SymbolType
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions, RE_name_score
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import math

class AutoUnstrip:
    def __init__(self, config):
        self.config = config
        self.auto_unstrip_distance = 0.09999999999999998
        self.base_addr = None
        self.path = None
        self.max_workers = 4 

    def _rename_function(self, bv: BinaryView, addr: int, new_name: str, new_name_mangled: str) -> bool:
        try:
            func = bv.get_function_at(addr)
            if not func:
                log_error(f"RevEng.AI | No function found at address {hex(addr)}")
                return False
            
            if func.name == new_name or func.name == new_name_mangled:
                log_info(f"RevEng.AI | Function at {hex(addr)} already has name {func.name}")
                return False
            
            new_symbol = Symbol(SymbolType.FunctionSymbol, addr, new_name)
            bv.define_user_symbol(new_symbol)
            
            log_info(f"RevEng.AI | Renamed function at {hex(addr)} to {new_name}")
            return True

        except Exception as e:
            log_error(f"RevEng.AI | Error renaming function at {hex(addr)}: {str(e)}")
            return False

    def _process_batch(self, function_ids: List[int], id_to_addr: Dict[int, int], bv: BinaryView) -> Tuple[int, List[str]]:
        """Process a batch of function IDs and return the number of renamed functions"""
        try:
            functions_by_distance = RE_nearest_symbols_batch(
                function_ids=function_ids,
                distance=self.auto_unstrip_distance,
                debug_enabled=True,
                nns=1
            ).json()["function_matches"]

            functions = []
            for function in functions_by_distance:
                functions.append({"function_id": function['origin_function_id'], "function_name": function['nearest_neighbor_function_name']})
            log_info(f"RevEng.AI | Functions by distance: {functions}")
            functions_by_score = RE_name_score(functions).json()["data"]
            log_info(f"RevEng.AI | Functions by score: {functions_by_score}")
            renamed_count = 0
            errors = []
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
                           if function['box_plot']["average"] < 0.9:
                                log_info(f"RevEng.AI | Function {function['function_id']} has a score of {function['box_plot']["average"]:.2f} for name {function['function_name']}, skipping")
                                break
                           else:
                                log_info(f"RevEng.AI | Function {function['function_id']} has a score of {function['box_plot']["average"]:.2f} for name {function['function_name']}, renaming")
                                if self._rename_function(bv, func_addr, new_name, new_name_mangled):
                                    renamed_count += 1
                                break
                    

                except Exception as e:
                    errors.append(str(e))

            return renamed_count, errors

        except Exception as e:
            return 0, [str(e)]

    def auto_unstrip(self, bv: BinaryView): 
        try:    
            log_info("RevEng.AI | Auto Unstripping binary")

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
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_chunk = {
                    executor.submit(self._process_batch, chunk, id_to_addr, bv): i 
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
            
            if all_errors:
                message += f"\nEncountered {len(all_errors)} errors during processing."
            
            log_info(f"RevEng.AI | {message}")
            return True, message

        except Exception as e:
            log_error(f"RevEng.AI | Error: {str(e)}")
            return False, str(e)