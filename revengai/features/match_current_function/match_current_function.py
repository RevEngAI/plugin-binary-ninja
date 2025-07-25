from binaryninja import BinaryView, log_info, log_error, Symbol, SymbolType
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions, RE_collections_search, RE_binaries_search, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import os
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from libbs.artifacts import _art_from_dict
from libbs.api import DecompilerInterface
from libbs.decompilers.binja.interface import BinjaInterface 
from revengai.utils.match_feature import MatchFeature
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

class MatchCurrentFunction(MatchFeature):
    def __init__(self, config):
        super().__init__(config)

    def match_functions(self, bv: BinaryView, options: Dict[str, Any]) -> List[Dict]:
        """Match functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function matching")

            similarity_threshold = 1.0 - (options.get("similarity_threshold", 90) * 0.01)
            selected_collections = options.get("selected_collections", [])
            debug_symbols = options.get("debug_symbols", False)
            debug_symbols_count = options.get("debug_symbols_count", 5)
            function_addr = options.get("function", None)
            result = { "matched": 0, "skipped": 0, "data": [] }

            functions_containing = bv.get_functions_containing(function_addr)
            
            if not functions_containing:
                log_error(f"RevEng.AI | Function not found at 0x{function_addr:x}")
                raise Exception("Function not found at address")
            
            function = functions_containing[0]
            log_info(f"RevEng.AI | Function: {function.name} at 0x{function.start:x}")

            filtered_collections = []
            filtered_binaries = []
            for item in selected_collections:
                if item["type"] == "Collection":
                    filtered_collections.append(item["id"])
                else:
                    filtered_binaries.append(item["id"])

            log_info(f"RevEng.AI | Similarity threshold: {similarity_threshold}")
            log_info(f"RevEng.AI | Selected collections: {selected_collections}")
            log_info(f"RevEng.AI | Debug symbols: {debug_symbols}")
            log_info(f"RevEng.AI | Debug symbols count: {debug_symbols_count}")
            log_info(f"RevEng.AI | Clicked address: 0x{function_addr:x}")

            binary_id = self.config.get_binary_id(bv)
            if not binary_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")
            
            analyzed_functions = RE_analyze_functions(self.path, binary_id).json()["functions"]

            analyzed_function = next((f for f in analyzed_functions if (f["function_vaddr"] + bv.image_base) == function.start), None)
            if not analyzed_function:
                log_error(f"RevEng.AI | Function {function.name} not found in analyzed functions")
                raise Exception("Function not found in analyzed functions")
            
            log_info(f"RevEng.AI | Found function {function.name} at 0x{function.start:x}")

            functions_by_distance = RE_nearest_symbols_batch(
                function_ids=[analyzed_function["function_id"]],
                distance=similarity_threshold,
                debug_enabled=debug_symbols,
                collections=filtered_collections,
                binaries=filtered_binaries,
                nns=debug_symbols_count
            ).json()["function_matches"]

            functions = []
            for function_by_distance in functions_by_distance:
                functions.append({"function_id": function_by_distance['origin_function_id'], "function_name": function_by_distance['nearest_neighbor_function_name']})
            if len(functions) == 0:
                return True, []
            functions_by_score = RE_name_score(functions).json()["data"]
            if len(functions_by_score) == 0:
                return True, []
            log_info(f"RevEng.AI | Found {len(functions_by_distance)} functions by distance")
            results = []
            for function_by_distance in functions_by_distance:
                try:
                    
                    matched_name = function_by_distance['nearest_neighbor_function_name'] if function_by_distance['nearest_neighbor_function_name'] else function_by_distance['nearest_neighbor_function_name_mangled']
                    matched_name_mangled = function_by_distance['nearest_neighbor_function_name_mangled'] if function_by_distance['nearest_neighbor_function_name_mangled'] else function_by_distance['nearest_neighbor_function_name']

                    functions = [{"function_id": function_by_distance['origin_function_id'], "function_name": matched_name_mangled}]
                    functions_by_score = RE_name_score(functions).json()["data"]
                    function_by_score = next((f for f in functions_by_score if f['function_id'] == function_by_distance['origin_function_id']), None)

                    confidence = function_by_score.get('box_plot', {}).get('average', 0) if function_by_score else 0

                    results.append({
                        "original_name": function.name if hasattr(function, 'name') else 'Unknown',
                        "matched_name": matched_name,
                        "matched_name_mangled": matched_name_mangled,
                        "signature": "N/A",
                        "matched_binary": function_by_distance['nearest_neighbor_binary_name'],
                        "similarity": f"{(function_by_distance['confidence'] * 100):.2f}%",
                        "confidence": f"{confidence:.2f}%",
                        "nearest_neighbor_id": function_by_distance['nearest_neighbor_id'],
                        "function_address": function.start if hasattr(function, 'start') else 0
                    })

                except Exception as e:
                    log_error(f"RevEng.AI | Error processing function {function_by_distance.get('origin_function_id', 'Unknown')}: {str(e)}")
            return True, results

        except Exception as e:
            log_error(f"RevEng.AI | Error in function matching: {str(e)}")
            return False, str(e)


    def rename_function(self, bv: BinaryView, selected_result: Dict) -> List[Dict]:
        try:
            log_info(f"RevEng.AI | Starting function renaming for {len(selected_result)} functions")
            
            renamed_count = 0
            failed_count = 0
            deci = BinjaInterface(bv)
            function_address = selected_result.get("function_address")
            new_name = selected_result.get("matched_name_mangled")
            
            if not function_address or not new_name:
                log_error(f"RevEng.AI | Missing function address or name for rename")
                failed_count += 1
                return False, "Missing function address or name for rename"
            
            if rename_function_util(bv, function_address, new_name):
                        renamed_count += 1
                        if selected_result.get('signature_data', None) is not None:
                            log_info(f"RevEng.AI | Applying data types for 0x{function_address:x}")
                            if deci is not None:
                                try:
                                    apply_data_types_util(function_address, selected_result['signature_data'], deci)
                                    log_info(f"RevEng.AI | Successfully applied data types for 0x{function_address:x}")
                                except Exception as e:
                                    log_error(f"RevEng.AI | Failed to apply data types for 0x{function_address:x}: {str(e)}")
            
            message = f"Successfully renamed {renamed_count} functions"
            if failed_count > 0:
                message += f" ({failed_count} failed)"
            
            log_info(f"RevEng.AI | {message}")
            return True, message
            
        except Exception as e:
            log_error(f"RevEng.AI | Error in function renaming: {str(e)}")
            return False, str(e)