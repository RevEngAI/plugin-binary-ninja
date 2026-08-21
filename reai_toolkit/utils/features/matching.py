from binaryninja import BinaryView, log_info, log_error
from typing import List, Dict, Tuple, Any
import revengai
import re
from libbs.artifacts import Function, FunctionArgument
from .datatypes import build_signature_data
from threading import Event
from concurrent.futures import ThreadPoolExecutor, as_completed

class MatchFeature:
    _POLL_INTERVAL = 3.0
    _POLL_TIMEOUT = 1200.0

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

    @staticmethod
    def _matching_error_message(messages) -> str:
        """Build a human-readable error from a matching workflow's progress messages."""
        if not messages:
            return "Function matching failed."
        errors = [m.text for m in messages if (getattr(m, "level", "") or "").upper() == "ERROR"]
        return "; ".join(errors or [messages[-1].text])


    # Search collections/Binaries Process Functions
    def search_items(self, bv: BinaryView, options: Dict[str, Any]):
        item_type = options.get("item_type")
        search_term = options.get("search_term")
        try:
            log_info(f"RevEng.AI | Searching {item_type} with term: '{search_term}'")
            query = self._parse_search_query(search_term)
            log_info(f"RevEng.AI | Query: {query}")
            if not self._is_query_empty(query):
                if item_type == "Collection":
                    items = self._search_collection(query)
                else:
                    items = self._search_binaries(query)
                log_info(f"RevEng.AI | Found {len(items)} {item_type.lower()} item(s)")
                if not items:
                    return False, "No items found"
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
    
    @staticmethod
    def _as_search_term(value: Any) -> str | None:
        if isinstance(value, list):
            value = value[0] if value else None
        return value or None

    def _search_collection(self, query: Dict[str, Any] = {}):
        try:
            output = []
            log_info("RevEng.AI | Searching for collections")
            search_term = self._as_search_term(query.get("collection_name") or query.get("query"))
            with self.config.create_api_client() as api_client:
                api_instance = revengai.CollectionsApi(api_client)
                api_response = api_instance.v3_list_collections(
                    search_term=search_term,
                    limit=20,
                    offset=0,
                )
                for collection in api_response.results or []:
                    item = {
                        "name": collection.collection_name,
                        "id": str(collection.collection_id),
                        "scope": collection.collection_scope,
                        "owner": collection.collection_owner,
                        "date": collection.updated_at.strftime("%m/%d/%Y %H:%M"),
                    }
                    output.append(item)
            return output
        except Exception as e:
            log_error(f"RevEng.AI | Error searching collections: {str(e)}")
            return []

    def _search_binaries(self, query: Dict[str, Any] = {}):
        output = []
        try:
            log_info("RevEng.AI | Searching for binaries")
            with self.config.create_api_client() as api_client:
                api_instance = revengai.SearchApi(api_client)
                api_response = api_instance.search_binaries(
                    page = 1, 
                    page_size = 20, 
                    partial_name = query.get("binary_name") , 
                    partial_sha256 = query.get("sha_256_hash"), 
                    tags = query.get("tags"), 
                    model_name = query.get("model_name")
                    
                )
                for binary in api_response.data.results:
                    item = {
                        "name": binary.binary_name,
                        "binary_id": str(binary.binary_id),
                        "analysis_id": str(binary.analysis_id),
                        "sha_256_hash": binary.sha_256_hash,
                        "owner": binary.owned_by,
                        "date": binary.created_at.strftime("%m/%d/%Y %H:%M"),
                    }
                    output.append(item)
            return output
        except Exception as e:
            log_error(f"RevEng.AI | Error searching collections: {str(e)}")
            return []

    # Fetch Data Types Process Functions
    def _process_data_type_batch(self, chunk: List[Dict], chunk_index: int) -> List[Dict]:
        try:
            log_info(f"RevEng.AI | Processing chunk of {len(chunk)} functions")
            function_ids = [result['nearest_neighbor_id'] for result in chunk]
            log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
            if self.cancelled.is_set():
                return []

            with self.config.create_api_client() as api_client:
                api_instance = revengai.DataTypesApi(api_client)
                api_response = api_instance.v3_list_function_signatures(
                    function_ids=function_ids,
                    include_data_types=True,
                ).to_dict()

            log_info(f"RevEng.AI | Cancelled: {self.cancelled.is_set()}")
            if self.cancelled.is_set():
                return []

            data_types = {}
            for group in api_response.get("data_types") or []:
                for entry in group.get("items") or []:
                    data_types[str(entry["data_type_id"])] = entry

            signatures = []
            for item in api_response.get("items") or []:
                if self.cancelled.is_set():
                    return []
                signature_data = build_signature_data(item, data_types)
                if signature_data is None:
                    continue
                for result in chunk:
                    if result['nearest_neighbor_id'] == item['function_id']:
                        fnc: Function = signature_data["function"]
                        log_info(f"Applying signature for {fnc.name}")
                        signature = self.function_to_str(fnc)
                        signatures.append({
                            "nearest_neighbor_id": result['nearest_neighbor_id'],
                            "signature": signature,
                            "data_types": data_types,
                            "signature_data": signature_data,
                        })
                        break

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

    def fetch_data_types(self, bv: BinaryView, selected_results: List[Dict]) -> Tuple[bool, Dict[str, Any]]:
        try:
            log_info("RevEng.AI | Starting data type fetching")
            #return False, "Not implemented"
            
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
   