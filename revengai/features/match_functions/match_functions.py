from binaryninja import BinaryView, log_info, log_error
from reait.api import RE_nearest_symbols_batch, RE_analyze_functions, RE_collections_search, RE_binaries_search, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from revengai.utils import rename_function as rename_function_util

class MatchFunctions:
    def __init__(self, config):
        self.config = config
        self.base_addr = None
        self.path = None
        self.binary_id = None
        self.analyzed_functions = []
        self.filtered_collections = []
        self.filtered_binaries = []

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
        try:
            log_info(f"RevEng.AI | Processing batch of {len(function_ids)} functions")

            functions_by_distance = RE_nearest_symbols_batch(
                function_ids=function_ids,
                debug_enabled=debug_symbols,
                collections=self.filtered_collections,
                binaries=self.filtered_binaries,
                nns=1
            ).json()["function_matches"]
            
            functions = []
            for function in functions_by_distance:
                functions.append({"function_id": function['origin_function_id'], "function_name": function['nearest_neighbor_function_name']})
            if len(functions) == 0:
                return 0, []
            functions_by_score = RE_name_score(functions).json()["data"]
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
            return 0, [str(e)]

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
            
            analyzed_functions = RE_analyze_functions(self.path, binary_id).json()["functions"]
            function_ids = []

            log_info(f"RevEng.AI | Found {len(analyzed_functions)} analyzed functions")

            functions = bv.functions
            len_functions = len(functions)

            log_info(f"RevEng.AI | Found {len_functions} functions and {len(analyzed_functions)} analyzed functions.")

            for index, function in enumerate(functions, 1):
                #log_info( f"RevEng.AI | Searching for {function.name} [{index}/{len_functions}]")
    
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

    def get_function_details(self, bv: BinaryView, function_address: int) -> Optional[Dict]:
        try:
            function = bv.get_function_at(function_address)
            if not function:
                return None
                
            return {
                "name": function.name,
                "address": hex(function_address),
                "size": len(function),
                "basic_blocks": len(function.basic_blocks),
                "instructions": sum(len(bb) for bb in function.basic_blocks),
                "call_sites": len(function.call_sites),
                "callers": len(function.callers),
                "callees": len(function.callees)
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
        """
        Check if the query dictionary is empty or contains only None values.

        Args:
            query (dict): The query dictionary to check

        Returns:
            bool: True if the query is empty, False otherwise
        """
        return all(value is None for value in query.values())
    
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

    def rename_functions(self, bv: BinaryView, selected_results: List[Dict]) -> List[Dict]:
        """Rename functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function renaming")

            renamed_count = 0
            for result in selected_results:
                # Convert function_address from string to int
                try:
                    addr = int(result['function_address'])
                except (ValueError, TypeError):
                    log_error(f"RevEng.AI | Invalid function address: {result}")
                    continue

                if rename_function_util(bv, addr, result['matched_name']):
                    renamed_count += 1

            success_message = f"Successfully renamed {renamed_count} functions!" if renamed_count > 0 else "No functions were renamed!"
                
            log_info(f"RevEng.AI | {success_message}")

            return True, success_message
        except Exception as e:
            log_error(f"RevEng.AI | Error renaming functions: {str(e)}")
            return False, str(e)
    
    def _process_data_type_batch(self, chunk: List[Dict]) -> List[Dict]:
        try:
            log_info(f"RevEng.AI | Processing chunk of {len(chunk)} functions")
            function_ids = set([result['nearest_neighbor_id'] for result in chunk])
            RE_functions_data_types(function_ids=list(function_ids))
            signatures = []
            while True:
                response = RE_functions_data_types_poll(    
                    function_ids=list(function_ids),
                ).json()
                data = response.get("data", {})
                total_count = data.get("total_count", 0)
                total_data_types = data.get("total_data_types_count", 0)
                items = data.get("items", [])
                log_info(f"RevEng.AI | Response: {response}")
                if not any(item.get("status") == "pending" for item in items):
                    break
                time.sleep(3)

            for item in items:
                log_info(f"RevEng.AI | Item: {item['function_id']}")
                for result in chunk:
                    if result['nearest_neighbor_id'] == item['function_id']:
                        signature = self.make_signature(item['data_types'])
                        if signature != "N/A":
                            signatures.append({"nearest_neighbor_id": result['nearest_neighbor_id'], "signature": signature})
                        break

            log_info(f"RevEng.AI | Total count: {total_count}")
            log_info(f"RevEng.AI | Total data types: {total_data_types}")
            log_info(f"RevEng.AI | Items: {items}")

            return signatures
        except Exception as e:
            log_error(f"RevEng.AI | Error processing data type batch: {str(e)}")
            return []
        
    def make_signature(self, data_types: List[Dict]) -> str:
        try:
            log_info(f"RevEng.AI | Making signature for {data_types}")
            signature = ""
            signature += f"{data_types['func_types'].get('type', 'N/A')} "

            for arg in data_types['func_types'].get('args', []):
                signature += f"{arg.get('type', 'N/A')}, "

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
            chunks = [selected_results[i:i + chunk_size] for i in range(0, len(selected_results), chunk_size)]

            log_info(f"RevEng.AI | Processing {len(selected_results)} functions in {len(chunks)} chunks of size {chunk_size}")

            signatures = []
            
            with ThreadPoolExecutor(max_workers=4) as executor:
                future_to_chunk = {
                    executor.submit(self._process_data_type_batch, chunk): i
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
