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
from threading import Event
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

class MatchCurrentFunction:
    def __init__(self, config):
        self.config = config
        self.base_addr = None
        self.path = None
        self.binary_id = None
        self.analyzed_functions = []
        self.filtered_collections = []
        self.filtered_binaries = []
        self.cancelled = Event()

    def search_collections(self, bv: BinaryView, search_term: str = ""):
        try:
            log_info(f"RevEng.AI | Searching collections with term: '{search_term}'")
            query = self._parse_search_query(search_term)
            log_info(f"RevEng.AI | Query: {query}")
            if not self._is_query_empty(query):
                items = self._search_collection(query)
                log_info(f"RevEng.AI | Items: {items}")
                return True, items
      
        except Exception as e:
            log_error(f"RevEng.AI | Error searching collections: {str(e)}")
            return False, str(e)

    def _process_batch(self, function_ids: List[int], id_to_addr: Dict[int, int], confidence_threshold: float, debug_symbols: bool, bv: BinaryView) -> Tuple[int, List[str]]:
        """Process a batch of function IDs and return the number of matched functions and any errors"""
        try:
            log_info(f"RevEng.AI | Processing batch of {len(function_ids)} functions")

            functions_by_distance = RE_nearest_symbols_batch(
                function_ids=function_ids,
                debug_enabled=self.debug_symbols,
                collections=self.filtered_collections,
                binaries=self.filtered_binaries,
                nns=self.debug_symbols_count
            ).json()["function_matches"]
            
            functions = []
            for function in functions_by_distance:
                functions.append({"function_id": function['origin_function_id'], "function_name": function['nearest_neighbor_function_name']})
            if len(functions) == 0:
                return 0, []
            #log_info(f"RevEng.AI | Functions by distance: {functions}")
            functions_by_score = RE_name_score(functions).json()["data"]
            #log_info(f"RevEng.AI | Functions by score: {functions_by_score}")
            matched_count = 0
            lines = []
            for result in functions_by_distance:
                try:
                    
                    line = {
                        "icon_path": f"{os.path.dirname(__file__)}/../../images/failed.png",
                        "icon_text": "Failed",
                        "original_name": "N/A",
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
                           
                           if function_by_score["box_plot"]["average"] < similarity_threshold:
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
                    
                    lines.append(line)
                    
                except Exception as e:
                    log_error(f"RevEng.AI | Error processing function {result['origin_function_id']}: {str(e)}")

            return matched_count, lines

        except Exception as e:
            log_error(f"RevEng.AI | Error processing batch: {str(e)}")
            return 0, [str(e)]

    def match_functions(self, bv: BinaryView, options: Dict[str, Any]) -> List[Dict]:
        """Match functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function matching")

            similarity_threshold = options.get("similarity_threshold", 90) * 0.01
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
                return 0, []
            functions_by_score = RE_name_score(functions).json()["data"]
            if len(functions_by_score) == 0:
                return 0, []
            
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
            raise

    def get_function_details(self, bv: BinaryView, function_address: int) -> Optional[Dict]:
        """Get detailed information about a specific function"""
        try:
            function = bv.get_function_at(function_address)
            if not function:
                return None
                
            return {
                "name": function.name,
                "address": function.start,
                "size": function.total_bytes,
                "signature": str(function.type),
                "basic_blocks": len(function.basic_blocks),
                "call_sites": len(function.call_sites),
                "callers": len(function.callers),
                "callees": len(function.callees),
            }
        except Exception as e:
            log_error(f"RevEng.AI | Error getting function details: {str(e)}")
            return None

    def _parse_search_query(self, query: str) -> dict:
        patterns = [
            "sha_256_hash",
            "tag",
            "binary_name",
            "collection_name",
            "function_name",
            "model_name"
        ]

        key_regex = "|".join(re.escape(p) for p in patterns)
        regex = rf'\b({key_regex}):\s*([^:]+?)(?=,\s*(?:{key_regex}):|$)'

        matches = re.findall(regex, query)

        result = {key: None for key in patterns + ["query"]}

        for key, value in matches:
            values = [v.strip() for v in value.split(',')]
            result[key] = values if len(values) > 1 or key == "tag" else values[0]

        if not any(value is not None for value in result.values()):
            result["query"] = query

        if result["tag"]:
            result["tags"] = result["tag"]
            del result["tag"]

        return result   

    def _is_query_empty(self, query: dict) -> bool:
        """Check if query is empty or contains only empty values"""
        if not query:
            return True
        
        return all(not str(v).strip() for v in query.values())

    def _search_collection(self, query: Dict[str, Any] = {}) -> None:
        
        def parse_date(date_str: str) -> str:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        def fetch_results(api_func, label: str) -> List[Dict[str, Any]]:
            try:
                log_info(f"RevEng.AI | Query: {query}")
                response = api_func(query=query, page=1, page_size=1024).json()
                results = response.get("data", {}).get("results", [])
                log_info(f"Found {len(results)} {label.lower()}s")
                return results
            
            except Exception as e:
                log_error(f"RevEng.AI | Getting information failed. Reason: {str(e)}")
                return []

        def build_items(items_list: List[Dict[str, Any]], item_type: str) -> List[Tuple]:
            items = []
            for item in items_list:
                name_key = "collection_name" if item_type == "Collection" else "binary_name"
                date_key = "last_updated_at" if item_type == "Collection" else "created_at"
                id_key = "collection_id" if item_type == "Collection" else "binary_id"
                icon = "lock.png" if item_type == "Collection" and item["scope"] == "PRIVATE" else \
                       "unlock.png" if item_type == "Collection" else "file.png"
                
                items.append({
                    "name": item[name_key],
                    "icon": icon,
                    "type": item_type,
                    "date": parse_date(item[date_key]),
                    "model_name": item["model_name"],
                    "owner": item["owned_by"],
                    "id": item[id_key]
                })
            return items

        try:

            log_info(f"RevEng.AI | Searching for collections with '{query or 'N/A'}'")

            collections_data = fetch_results(RE_collections_search, "collection")
            binaries_data = fetch_results(RE_binaries_search, "binary")

            table_items = build_items(collections_data, "Collection")
            table_items += build_items(binaries_data, "Binary")

            return table_items

        except Exception as e:
            log_error("Getting collections failed. Reason: %s", str(e))
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

    def _process_data_type_batch(self, chunk: List[Dict], chunk_index: int) -> List[Dict]:
        try:
            log_info(f"RevEng.AI | Processing chunk of {len(chunk)} functions")
            function_ids = set([result['nearest_neighbor_id'] for result in chunk])
            log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
            if self.cancelled.is_set():
                return []
            
            RE_functions_data_types(function_ids=list(function_ids))
            log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
            if self.cancelled.is_set():
                return []
            signatures = []
            items = []
            while True:
                if self.cancelled.is_set():
                    return []
                
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
                log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
                if self.cancelled.is_set():
                    return []
                log_info(f"RevEng.AI | Item: {item['function_id']}")
                if item['status'] != "completed":
                    continue
                for result in chunk:
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
                            log_info(f"Applying signature for {fnc.name}")
                            signature = self.function_to_str(fnc)
                            if signature != "N/A":
                                signatures.append({"nearest_neighbor_id": result['nearest_neighbor_id'], "signature": signature, "data_types": item['data_types'], "signature_data": {"deps": func_deps, "function": fnc}})
                        break

            #log_info(f"RevEng.AI | Total count: {total_count}")
            #log_info(f"RevEng.AI | Total data types: {total_data_types}")
            #log_info(f"RevEng.AI | Items: {items}")

            return signatures
        except Exception as e:
            log_error(f"RevEng.AI | Error processing data type batch: {str(e)}")
            return []
        
    def make_signature(self, data_types: List[Dict]) -> str:
        try:
            #log_info(f"RevEng.AI | Making signature for {data_types}")
            signature = "("
            for _, arg in data_types['func_types'].get('header', {}).get('args', {}).items():
                #log_info(f"RevEng.AI | Arg: {arg}")
                signature += f"{arg.get('type', 'N/A')}, "
            signature = signature[:-2] if signature.endswith(", ") else signature

            signature += f") {data_types['func_types'].get('type', 'N/A')}"

            log_info(f"RevEng.AI | Signature: {signature}")
            return signature
        except Exception as e:
            log_error(f"RevEng.AI | Error making signature: {str(e)}")
            return "N/A"

    def fetch_data_types(self, bv: BinaryView, selected_results: List[Dict]) -> Tuple[bool, Dict[str, Any]]:
        try:
            log_info("RevEng.AI | Starting data type fetching")
            
            if len(selected_results) == 0:
                return False, "No valid functions selected"

            chunk_size = 50
            if len(selected_results) < chunk_size:
                chunks = [selected_results]
            else:
                chunks = [selected_results[i:i + chunk_size] for i in range(0, len(selected_results), chunk_size)]

            log_info(f"RevEng.AI | Processing {len(selected_results)} functions in {len(chunks)} chunks of size {chunk_size}")

            signatures = []
            if self.cancelled.is_set():
                return False, "Operation cancelled"
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_chunk = {
                    executor.submit(self._process_data_type_batch, chunk, i): i
                    for i, chunk in enumerate(chunks)
                }

                for future in as_completed(future_to_chunk):
                    chunk_index = future_to_chunk[future]
                    try:
                        chunk = future.result()
                        log_info(f"RevEng.AI | Chunk {chunk_index} completed")
                        signatures.extend(chunk)
        
                    except Exception as e:
                        log_error(f"RevEng.AI | Error processing chunk {chunk_index}: {str(e)}")

            options = {
                "success_count": len(signatures),
                "signatures": signatures
            }

            return True, options
        except Exception as e:
            log_error(f"RevEng.AI | Error fetching data types: {str(e)}")
            return False, str(e)
        
    def function_arguments(self, fnc: Function) -> list[str]:
        args = []
        for k in fnc.header.args:
            arg: FunctionArgument = fnc.header.args[k]
            args.append(
                f"{arg.type} {arg.name}"
            )
        return args
            
    def function_to_str(self, fnc: Function) -> str:
        # convert the signature to a string representation
        return f"{fnc.type} {fnc.name}"\
            f"({', '.join(self.function_arguments(fnc))})"
    
    def cancel(self):
        log_info("RevEng.AI | Cancelling operation...")
        self.cancelled.set()

    def clear_cancelled(self):
        log_info("RevEng.AI | Clearing cancelled event...")
        self.cancelled.clear()