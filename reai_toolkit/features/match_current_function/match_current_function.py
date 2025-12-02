import os
from libbs.api import DecompilerInterface
from typing import List, Dict, Tuple, Any
from binaryninja import BinaryView, log_info, log_error
from libbs.decompilers.binja.interface import BinjaInterface
from concurrent.futures import ThreadPoolExecutor, as_completed
from reai_toolkit.utils import MatchFeature, rename_function as rename_function_util, apply_data_types as apply_data_types_util
import revengai
import time

class MatchCurrentFunction(MatchFeature):
    def __init__(self, config):
        super().__init__(config)


    def match_functions(self, bv: BinaryView, options: Dict[str, Any]) -> List[Dict]:
        def parse_confidence(item):
                try:
                    return float(item["confidence"].strip('%'))
                except (KeyError, ValueError):
                    return 0.0
        try:
            log_info("RevEng.AI | Starting function matching")

            similarity_threshold = options.get("similarity_threshold", 90)
            selected_collections_string = options.get("selected_collections", "")
            selected_collections = []
            selected_binaries_string = options.get("selected_binaries", "")
            selected_binaries = []
            debug_symbols = options.get("debug_symbols", False)
            result = { "matched": 0, "skipped": 0, "data": [] }
            function_addr = options.get("function", None)

            functions_containing = bv.get_functions_containing(function_addr)
            
            if not functions_containing:
                log_error(f"RevEng.AI | Function not found at 0x{function_addr:x}")
                raise Exception("Function not found at address")
            
            function = functions_containing[0]
            log_info(f"RevEng.AI | Function: {function.name} at 0x{function.start:x}")

            if selected_collections_string:
                selected_collections = [int(c) for c in selected_collections_string.split(",")]
            if selected_binaries_string:
                selected_binaries = [int(b) for b in selected_binaries_string.split(",")]
            
            log_info(f"RevEng.AI | Selected collections: {selected_collections}")
            log_info(f"RevEng.AI | Selected binaries: {selected_binaries}")

            log_info(f"RevEng.AI | Similarity threshold: {similarity_threshold}")
            log_info(f"RevEng.AI | Debug symbols: {debug_symbols}")
            log_info(f"RevEng.AI | Clicked address: 0x{function_addr:x}")

            analysis_id = self.config.get_analysis_id(bv)
            if not analysis_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")
            
            if self.cancelled.is_set():
                return False, "Operation cancelled"
            
            with revengai.ApiClient(self.config.api_config) as api_client:
                analysis_core_instance = revengai.AnalysesResultsMetadataApi(api_client)
                analyzed_functions = analysis_core_instance.get_functions_list(analysis_id)
                analyzed_functions = analyzed_functions.to_dict()["data"]["functions"]
            if self.cancelled.is_set():
                return False, "Operation cancelled"
            
            function_ids = []

            log_info(f"RevEng.AI | Found {len(analyzed_functions)} analyzed functions")

            functions = bv.functions
            len_functions = len(functions)

            log_info(f"RevEng.AI | Found {len_functions} functions and {len(analyzed_functions)} analyzed functions.")

            analyzed_function = next((f for f in analyzed_functions if f["function_vaddr"] == function.start), None)
            if not analyzed_function:
                log_error(f"RevEng.AI | Function {function.name} not found in analyzed functions")
                raise Exception("Function not found in analyzed functions")

            log_info(f"RevEng.AI | Found analyzed function {analyzed_function['function_name']} at 0x{analyzed_function['function_vaddr']:x}")

            id_to_addr = {
                func["function_id"]: func["function_vaddr"]
                for func in analyzed_functions
            }

            total_matched_functions = 0
            filters = revengai.FunctionMatchingFilters.from_dict({
                "collections": selected_collections,
                "binaries": selected_binaries
            })
            
            schema_ann_model = revengai.FunctionMatchingRequest.from_dict({
                "model_id": self.config.model_id,
                "function_ids": [analyzed_function["function_id"]],
                "filters": filters,
                "result_per_function": 20,
                "min_similarity": similarity_threshold
            })
            matched_count = 0
            while True:
                time.sleep(3)
                with revengai.ApiClient(self.config.api_config) as api_client:
                    analysis_core_instance = revengai.FunctionsCoreApi(api_client)
                    functions_by_distance = analysis_core_instance.batch_function_matching( schema_ann_model)

                    #################
                    for function_by_distance in functions_by_distance.matches:
                        try:
                            if len(function_by_distance.matched_functions) == 0:
                                continue
                            log_info(f"RevEng.AI | Matched function: {function_by_distance.matched_functions[0]}")
                            line = {
                                "icon_path": f"{os.path.dirname(__file__)}/../../images/failed.png",
                                "icon_text": "Failed",
                                "matched_function_name": function_by_distance.matched_functions[0].function_name,
                                "signature": "N/A",
                                "matched_hash": function_by_distance.matched_functions[0].sha_256_hash,
                                "matched_binary_name": function_by_distance.matched_functions[0].binary_name,
                                "similarity": f"{(function_by_distance.matched_functions[0].similarity):.2f}%",
                                "confidence": f"{(function_by_distance.matched_functions[0].confidence):.2f}%",
                                "nearest_neighbor_id": function_by_distance.matched_functions[0].function_id,
                            }

                            func_addr = function_by_distance.matched_functions[0].function_vaddr
                            log_info(f"RevEng.AI | Function address: {func_addr:x}")
                            log_info(f"RevEng.AI | Function ID: {function_by_distance.function_id}")
                            if not func_addr:
                                line["error"] = "Function not found in binary"
                                if line not in result["data"]:
                                    result["data"].append(line)
                                continue
                            
                            function = bv.get_function_at(func_addr)
                            line["function_address"] = func_addr 
                            log_info(f"RevEng.AI | Function: {function} at {func_addr:x}")

                            if not line["matched_function_name"] or line["matched_function_name"].startswith(("sub_", "FUN_")):
                                    line["error"] = "Function name is also debug symbol"
                                    log_info(f"RevEng.AI | Function name is also debug symbol: {line}")
                                    if line not in result["data"]:
                                        result["data"].append(line)
                                    continue
                            
                            if function_by_distance.matched_functions[0].similarity < similarity_threshold:
                                    line["error"] = "Function score is below confidence threshold"
                                    log_info(f"RevEng.AI | Function score is below confidence threshold: {line}")
                            else:
                                    line["icon_path"] = f"{os.path.dirname(__file__)}/../../images/success.png"
                                    line["icon_text"] = "Success"
                                    matched_count += 1
                                    
                            if line not in result["data"]:
                                result["data"].append(line)

                        except Exception as e:
                            log_error(f"RevEng.AI | Error processing function {function_by_distance.function_id}: {str(e)}")
                    #populate_table_function(result["data"])
                    #################
                    if functions_by_distance.status.lower() == "completed":
                        break
                    elif functions_by_distance.status.lower() == "error":
                        raise Exception("Function matching failed")
            sorted_list = sorted(result["data"], key=parse_confidence, reverse=True)
            result["data"] = sorted_list
            #populate_table_function(result["data"])
            result["failed"] = len(analyzed_functions) - matched_count
            result["matched"] = matched_count

            if self.cancelled.is_set():
                return False, "Operation cancelled"
    
            return True, result
            
        except Exception as e:
            log_error(f"RevEng.AI | Error matching functions: {str(e)}")
            raise e


    def _process_rename_batch(self, chunk: List[Dict], bv: BinaryView, deci: DecompilerInterface = None) -> Tuple[int, int]:
        try:
            log_info(f"RevEng.AI | Processing chunk of {len(chunk)} functions")
            renamed_count = 0
            datatype_count = 0
            for result in chunk:
                try:
                    if self.cancelled.is_set():
                        return 0, 0
                    
                    addr = int(result['function_address'])
                    if rename_function_util(bv, addr, result["matched_function_name"]):
                        renamed_count += 1
                        
                        if result.get('signature_data', None) is not None:
                            log_info(f"RevEng.AI | Applying data types for 0x{addr:x}")
                            
                            if deci is not None:
                                log_info(f"RevEng.AI | Applying data types for 0x{addr:x} with decompiler {deci}")
                                try:
                                    apply_data_types_util(addr, result['signature_data'], deci)
                                    datatype_count += 1
                                    log_info(f"RevEng.AI | Successfully applied data types for 0x{addr:x}")
                                except Exception as e:
                                    log_error(f"RevEng.AI | Failed to apply data types for 0x{addr:x}: {str(e)}")
                        
                        
                except (ValueError, TypeError):
                    log_error(f"RevEng.AI | Invalid function address: {result}")
                    continue

            return renamed_count, datatype_count
                
        except Exception as e:
            log_error(f"RevEng.AI | Error processing rename batch: {str(e)}")
            return 0, 0


    def rename_functions(self, bv: BinaryView, selected_results: List[Dict]) -> List[Dict]:
        """Rename functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function renaming")
            total_renamed_count = 0
            chunk_size = 50
            deci = BinjaInterface(bv)
            chunks = [selected_results[i:i + chunk_size] for i in range(0, len(selected_results), chunk_size)]

            log_info(f"RevEng.AI | Processing {len(selected_results)} functions in {len(chunks)} chunks of size {chunk_size}")

            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_chunk = {
                    executor.submit(self._process_rename_batch, chunk, bv, deci): i 
                    for i, chunk in enumerate(chunks)
                }

                for future in as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:    
                        renamed_count, datatype_count = future.result()
                        total_renamed_count += renamed_count
                        log_info(f"RevEng.AI | Chunk {chunk_index} completed: renamed {renamed_count} functions, applied {datatype_count} data types")
                    except Exception as e:
                        log_error(f"RevEng.AI | Error processing chunk {chunk_index}: {str(e)}")
            
            success_message = f"Successfully renamed {total_renamed_count} functions!" if total_renamed_count > 0 else "No functions were renamed!"
                
            log_info(f"RevEng.AI | {success_message}")

            return True, success_message
        except Exception as e:
            log_error(f"RevEng.AI | Error renaming functions: {str(e)}")
            return False, str(e)
    