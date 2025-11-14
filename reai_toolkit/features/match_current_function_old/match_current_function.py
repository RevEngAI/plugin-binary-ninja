from typing import List, Dict, Any
import revengai
import time
from binaryninja import BinaryView, log_info, log_error
from libbs.decompilers.binja.interface import BinjaInterface 
from reait.api import RE_nearest_symbols_batch, RE_analyze_functions, RE_name_score
from reai_toolkit.utils import MatchFeature, rename_function as rename_function_util, apply_data_types as apply_data_types_util

class MatchCurrentFunction(MatchFeature):
    def __init__(self, config):
        super().__init__(config)

    def match_functions(self, bv: BinaryView, options: Dict[str, Any]) -> List[Dict]:
        """Match functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function matching")

            similarity_threshold = options.get("similarity_threshold", 90)
            selected_collections = options.get("selected_collections", [])
            debug_symbols = options.get("debug_symbols", False)
            
            function_addr = options.get("function", None)

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
            

            binary_id = self.config.get_binary_id(bv)
            if not binary_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")

            analysis_id = self.config.get_analysis_id(bv)
            if not analysis_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")

            with revengai.ApiClient(self.config.api_config) as api_client:
                analysis_core_instance = revengai.AnalysesResultsMetadataApi(api_client)
                analyzed_functions = analysis_core_instance.get_functions_list(analysis_id)
                analyzed_functions = analyzed_functions.to_dict()["data"]["functions"]

            analyzed_function = next((f for f in analyzed_functions if f["function_vaddr"] == function.start), None)
            if not analyzed_function:
                log_error(f"RevEng.AI | Function {function.name} not found in analyzed functions")
                raise Exception("Function not found in analyzed functions")
            
            log_info(f"RevEng.AI | Found function {function.name} at 0x{function.start:x}")

            filters = revengai.FunctionMatchingFilters.from_dict({
                "collections": self.filtered_collections,
                "binaries": self.filtered_binaries
            })
            
            schema_ann_model = revengai.FunctionMatchingRequest.from_dict({
                "model_id": 12,
                "function_ids": [analyzed_function["function_id"]],
                "filters": filters,
                "result_per_function": 20,
                "min_similarity": similarity_threshold
            })

            functions = []

            while True:
                time.sleep(3)
                with revengai.ApiClient(self.config.api_config) as api_client:
                    api_instance = revengai.FunctionsCoreApi(api_client)
                    api_response = api_instance.batch_function_matching(analysis_id, schema_ann_model)
                if api_response.status.lower() == "completed":
                    for function_by_distance in api_response.matches:
                        if len(function_by_distance.matched_functions) == 0:
                            continue
                        try:
                            functions.append({
                                "original_name": function.name if hasattr(function, 'name') else 'Unknown',
                                "matched_name": function_by_distance.matched_functions[0].function_name,
                                "matched_name_mangled": function_by_distance.matched_functions[0].function_name,
                                "signature": "N/A",
                                "matched_binary": function_by_distance.matched_functions[0].binary_name,
                                "similarity": f"{function_by_distance.matched_functions[0].similarity:.2f}%",
                                "confidence": f"{function_by_distance.matched_functions[0].confidence:.2f}%",
                                "nearest_neighbor_id": function_by_distance.matched_functions[0].function_id,
                                "function_address": function.start if hasattr(function, 'start') else 0
                            })
                            functions.append({"function_id": function_by_distance['origin_function_id'], "function_name": function_by_distance['nearest_neighbor_function_name']})
                        except Exception as e:
                            log_error(f"RevEng.AI | Error processing function {function_by_distance.matched_functions[0].function_id}: {str(e)}")
                    break
                elif api_response.status.lower() == "error":
                        raise Exception("Function matching failed")
            return True, functions

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