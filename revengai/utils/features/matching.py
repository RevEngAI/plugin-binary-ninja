from binaryninja import BinaryView, log_info, log_error
from reait.api import RE_collections_search, RE_binaries_search, RE_functions_data_types, RE_functions_data_types_poll
from typing import List, Dict, Tuple, Any
from datetime import datetime
import re
import time
from libbs.artifacts import _art_from_dict, Function, FunctionArgument
from threading import Event
from concurrent.futures import ThreadPoolExecutor, as_completed

class MatchFeature:
    def __init__(self, config):
        self.config = config
        self.base_addr = None
        self.path = None
        self.binary_id = None
        self.analyzed_functions = []
        self.filtered_collections = []
        self.filtered_binaries = []
        self.cancelled = Event()
     
    # Cancel/Clear Process Functions
    def cancel(self):
        log_info("RevEng.AI | Cancelling operation...")
        self.cancelled.set()

    def clear_cancelled(self):
        log_info("RevEng.AI | Clearing cancelled event...")
        self.cancelled.clear()
    

    # Search collections/Binaries Process Functions
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
        
    def _is_query_empty(self, query: dict) -> bool:
        return all(value is None for value in query.values())

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

    
    # Fetch Data Types Process Functions
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
            
            log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
            if self.cancelled.is_set():
                return False, "Operation cancelled"

            chunk_size = 50
            if len(selected_results) < chunk_size:
                chunks = [selected_results]
            else:
                chunks = [selected_results[i:i + chunk_size] for i in range(0, len(selected_results), chunk_size)]

            log_info(f"RevEng.AI | Processing {len(selected_results)} functions in {len(chunks)} chunks of size {chunk_size}")

            signatures = []
            log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
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
   