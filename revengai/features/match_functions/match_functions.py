from binaryninja import BinaryView, log_info, log_error
from reait.api import RE_nearest_symbols_batch, RE_analyze_functions, RE_collections_search, RE_binaries_search, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import os
import re
import time
from libbs.artifacts import _art_from_dict
from libbs.api import DecompilerInterface
from libbs.decompilers.binja.interface import BinjaInterface 
from revengai.utils.match_feature import MatchFeature
from threading import Event
from concurrent.futures import ThreadPoolExecutor, as_completed
from revengai.utils import rename_function as rename_function_util
from revengai.utils import apply_data_types as apply_data_types_util
from libbs.artifacts import (
    Function,
    FunctionArgument,
    GlobalVariable,
    Enum,
    Struct,
    Typedef,
)

class MatchFunctions(MatchFeature):
    def __init__(self, config):
        super().__init__(config)

    
    # Match Functions Process Functions
    def _process_batch(self, function_ids: List[int], id_to_addr: Dict[int, int], confidence_threshold: float, debug_symbols: bool, bv: BinaryView) -> Tuple[int, List[str]]:
        try:
            log_info(f"RevEng.AI | Processing batch of {len(function_ids)} functions")
            if self.cancelled.is_set():
                return 0, []
            
            functions_by_distance = RE_nearest_symbols_batch(
                function_ids=function_ids,
                debug_enabled=debug_symbols,
                collections=self.filtered_collections,
                binaries=self.filtered_binaries,
                nns=1
            ).json()["function_matches"]
            
            if self.cancelled.is_set():
                return 0, []
            
            functions = []
            for function in functions_by_distance:
                functions.append({"function_id": function['origin_function_id'], "function_name": function['nearest_neighbor_function_name']})
            if len(functions) == 0:
                return 0, []
            functions_by_score = RE_name_score(functions).json()["data"]
            if self.cancelled.is_set():
                return 0, []
            
            matched_count = 0
            lines = []
            for result in functions_by_distance:
                try:
                    if self.cancelled.is_set():
                        return 0, []
                    
                    line = {
                        "icon_path": f"{os.path.dirname(__file__)}/../../images/failed.png",
                        "icon_text": "Failed",
                        "original_name": "N/A",
                        "demangled_name": result['nearest_neighbor_function_name'] if result['nearest_neighbor_function_name'] else result['nearest_neighbor_function_name_mangled'],
                        "matched_name": result['nearest_neighbor_function_name_mangled'] if result['nearest_neighbor_function_name_mangled'] else result['nearest_neighbor_function_name'],
                        "signature": "N/A",
                        "matched_binary": result['nearest_neighbor_binary_name'],
                        "similarity": f"{(result['confidence'] * 100):.2f}%",
                        "confidence": "N/A",
                        "error": "",
                        "nearest_neighbor_id": result['nearest_neighbor_id'],
                        "function_address": "N/A"
                    }

                    func_addr = id_to_addr.get(result['origin_function_id'])
                    if not func_addr:
                        line["error"] = "Function not found in binary"
                        lines.append(line)
                        continue
                    
                    function = bv.get_function_at(func_addr)
                    if function:
                        line["original_name"] = function.name
                        line["function_address"] = function.start

                    for function_by_score in functions_by_score:
                        if function_by_score['function_id'] == result['origin_function_id']:
                           
                           line["confidence"] = f"{function_by_score['box_plot']['average']:.2f}%"

                           if not line["matched_name"] or line["matched_name"].startswith(("sub_", "FUN_")):
                                line["error"] = "Function name is also debug symbol"
                                log_info(f"RevEng.AI | Function name is also debug symbol: {line}")
                                break
                           
                           if function_by_score["box_plot"]["average"] < confidence_threshold:
                                line["error"] = "Function score is below confidence threshold"
                                break
                           else:
                                function = bv.get_function_at(id_to_addr.get(result['origin_function_id']))
                                if not function:
                                    log_error(f"RevEng.AI | Function not found: ID = {result['origin_function_id']} | Address = 0x{id_to_addr.get(result['origin_function_id']):x}")
                                line["icon_path"] = f"{os.path.dirname(__file__)}/../../images/success.png"
                                line["icon_text"] = "Success"
                                matched_count += 1
                                break
                            
                    if line not in lines:
                        lines.append(line)
                    
                except Exception as e:
                    log_error(f"RevEng.AI | Error processing function {result['origin_function_id']}: {str(e)}")

            return matched_count, lines

        except Exception as e:
            log_error(f"RevEng.AI | Error processing batch: {str(e)}")
            return 0, []

    def match_functions(self, bv: BinaryView, options: Dict[str, Any]) -> List[Dict]:
        try:
            log_info("RevEng.AI | Starting function matching")

            confidence_threshold = options.get("confidence_threshold", 0.1)
            selected_collections = options.get("selected_collections", [])
            debug_symbols = options.get("debug_symbols", False)
            result = { "matched": 0, "skipped": 0, "data": [] }

            self.filtered_collections = []
            self.filtered_binaries = []
            for item in selected_collections:
                if item["type"] == "Collection":
                    self.filtered_collections.append(item["id"])
                else:
                    self.filtered_binaries.append(item["id"])

            log_info(f"RevEng.AI | Confidence threshold: {confidence_threshold}")
            log_info(f"RevEng.AI | Selected collections: {selected_collections}")
            log_info(f"RevEng.AI | Debug symbols: {debug_symbols}")

            binary_id = self.config.get_binary_id(bv)
            if not binary_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")
            
            if self.cancelled.is_set():
                return False, "Operation cancelled"
            
            analyzed_functions = RE_analyze_functions(self.path, binary_id).json()["functions"]
            if self.cancelled.is_set():
                return False, "Operation cancelled"
            
            function_ids = []

            log_info(f"RevEng.AI | Found {len(analyzed_functions)} analyzed functions")

            functions = bv.functions
            len_functions = len(functions)

            log_info(f"RevEng.AI | Found {len_functions} functions and {len(analyzed_functions)} analyzed functions.")

            for index, function in enumerate(functions, 1):
                #log_info( f"RevEng.AI | Searching for {function.name} [{index}/{len_functions}]")
                if self.cancelled.is_set():
                    return False, "Operation cancelled"
                
                analyzed_function = next((f for f in analyzed_functions if (f["function_vaddr"] + bv.image_base) == function.start), None)

                if analyzed_function:
                    #log_info(f"RevEng.AI | Found function {function.name} at {function.start:x}")
                    function_ids.append(analyzed_function["function_id"])
                else:
                    result["skipped"] += 1 
                    result["data"].append({
                        "icon_path": f"{os.path.dirname(__file__)}/../../images/failed.png",
                        "icon_text": "Failed",
                        "original_name": function.name,
                        "demangled_name": "N/A",
                        "matched_name": "N/A",
                        "signature": "N/A",
                        "matched_binary": "N/A",
                        "similarity": "0.0%",
                        "confidence": "0.0%",
                        "error": "No Similar Function Found",
                        "function_address": function.start
                    })
            
            chunk_size = 50
            chunks = [function_ids[i:i + chunk_size] for i in range(0, len(function_ids), chunk_size)]

            log_info(f"RevEng.AI | Processing {len(function_ids)} functions in {len(chunks)} chunks of size {chunk_size}")

            id_to_addr = {
                func["function_id"]: func["function_vaddr"] + bv.image_base
                for func in analyzed_functions
            }

            total_matched_functions = 0
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_chunk = {
                    executor.submit(self._process_batch, chunk, id_to_addr, confidence_threshold, debug_symbols, bv): i 
                    for i, chunk in enumerate(chunks)
                }

                for future in as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:    
                        matched_count, lines = future.result()
                        total_matched_functions += matched_count
                        result["data"].extend(lines)
                        log_info(f"RevEng.AI | Chunk {chunk_index} completed: matched {matched_count} functions")
                    except Exception as e:
                        log_error(f"RevEng.AI | Error processing chunk {chunk_index}: {str(e)}")
            
            result["matched"] = total_matched_functions
            result["failed"] = len(analyzed_functions) - total_matched_functions - result["skipped"]
            
            def parse_confidence(item):
                try:
                    return float(item["confidence"].strip('%'))
                except (KeyError, ValueError):
                    return 0.0
            
            #sorted_list = sorted(result["data"], key=lambda x: int(x["function_address"]) if x["function_address"] != "N/A" else 0)
            sorted_list = sorted(result["data"], key=parse_confidence, reverse=True)

            #seen = {}
            #sorted_list = [seen.setdefault(str(x), x) for x in sorted_list if str(x) not in seen]

            result["data"] = sorted_list
            
            return True, result
            
        except Exception as e:
            log_error(f"RevEng.AI | Error matching functions: {str(e)}")
            raise e


    # Rename Functions Process Functions
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
                    if rename_function_util(bv, addr, result['matched_name']):
                        renamed_count += 1
                        if result.get('signature_data', None) is not None:
                            log_info(f"RevEng.AI | Applying data types for 0x{addr:x}")
                            if deci is not None:
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
    