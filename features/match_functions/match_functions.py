from binaryninja import BinaryView, log_info, log_error, Function
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions
from typing import List, Dict, Tuple, Optional
import json

class MatchFunctions:
    def __init__(self, config):
        self.config = config
        self.base_addr = None
        self.path = None
        self.binary_id = None
        self.analyzed_functions = []

    def search_collections(self, bv: BinaryView, search_term: str = "") -> List[Dict]:
        try:
            log_info(f"RevEng.AI | Searching collections with term: '{search_term}'")
            query = self._parse_search_query(search_term)
            log_info(f"RevEng.AI | Query: {query}")
            
            # Since RE_collections might not be available, we'll use RE_search to find binaries
            # and simulate collections based on search results
            """
            search_results = RE_search(fpath=bv.file.filename, search_term=search_term).json()
            
            if "query_results" not in search_results:
                log_error("RevEng.AI | No search results found")
                return []
                
            query_results = search_results["query_results"]
            
            # Convert search results to collection-like format
            collections = []
            for i, result in enumerate(query_results[:20]):  # Limit to 20 results
                collection = {
                    "id": str(i),
                    "name": result.get("binary_name", f"Binary_{i}"),
                    "type": "Binary",
                    "date": result.get("upload_date", "Unknown"),
                    "model_name": result.get("model", "Unknown"),
                    "owner": "RevEng.AI",
                    "binary_data": result  # Store original data
                }
                collections.append(collection)
            
            log_info(f"RevEng.AI | Found {len(collections)} collections")
            return collections
            """            
        except Exception as e:
            log_error(f"RevEng.AI | Error searching collections: {str(e)}")
            return False, str(e)

    def get_collection_functions(self, collection_id: str) -> List[Dict]:
        """Get functions from a specific collection (simulated)"""
        try:
            log_info(f"RevEng.AI | Getting functions from collection {collection_id}")
            
            # For now, return a simulated list of functions
            # In a real implementation, this would query the API for functions in the collection
            functions = [
                {
                    "function_id": f"func_{i}",
                    "function_name": f"function_{i}",
                    "signature": f"void function_{i}()",
                    "binary_name": f"collection_{collection_id}"
                }
                for i in range(10)  # Simulate 10 functions
            ]
            
            log_info(f"RevEng.AI | Found {len(functions)} functions in collection")
            return functions
            
        except Exception as e:
            log_error(f"RevEng.AI | Error getting collection functions: {str(e)}")
            return []

    def match_functions(self, bv: BinaryView, distance_threshold: float = 0.1, max_matches: int = 10) -> List[Dict]:
        """Match functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function matching")
            
            self.base_addr = bv.image_base
            self.path = bv.file.filename
            self.binary_id = self.config.get_binary_id(bv)
            
            log_info(f"RevEng.AI | Binary path: {self.path}")
            log_info(f"RevEng.AI | Binary ID: {self.binary_id}")
            
            # Search for the binary
            search_results = RE_search(fpath=self.path).json()["query_results"]
            log_info(f"RevEng.AI | Search results: {len(search_results)} found")
            
            if not search_results:
                raise Exception("Binary not found in RevEng.AI database. Please upload the binary first.")
            
            # Get analyzed functions
            self.analyzed_functions = RE_analyze_functions(self.path, self.binary_id).json()["functions"]
            function_ids = [func["function_id"] for func in self.analyzed_functions]
            
            log_info(f"RevEng.AI | Found {len(function_ids)} functions to match")
            
            # Create address mapping
            id_to_addr = {
                func["function_id"]: func["function_vaddr"] + self.base_addr
                for func in self.analyzed_functions
            }
            
            # Batch match functions
            matches_result = RE_nearest_symbols_batch(
                function_ids=function_ids,
                distance=distance_threshold,
                debug_enabled=True,
                nns=max_matches
            ).json()
            
            if "function_matches" not in matches_result:
                log_error("RevEng.AI | No function matches found in response")
                return []
            
            function_matches = matches_result["function_matches"]
            
            # Enrich matches with additional information
            enriched_matches = []
            for match in function_matches:
                func_id = match.get("origin_function_id")
                func_addr = id_to_addr.get(func_id)
                
                if func_addr:
                    # Get the Binary Ninja function
                    bn_function = bv.get_function_at(func_addr)
                    
                    # Calculate similarity and confidence
                    distance = match.get("distance", 1.0)
                    similarity_percentage = (1.0 - distance) * 100
                    confidence_percentage = similarity_percentage
                    
                    # Determine if match is successful
                    matched_name = match.get("nearest_neighbor_function_name", "N/A")
                    is_successful = (matched_name and 
                                   matched_name != "N/A" and 
                                   not matched_name.startswith(("sub_", "FUN_")) and
                                   similarity_percentage >= 90.0)  # High confidence threshold
                    
                    enriched_match = {
                        "function_id": func_id,
                        "function_address": func_addr,
                        "original_name": bn_function.name if bn_function else f"sub_{func_addr:X}",
                        "matched_name": matched_name,
                        "matched_name_mangled": match.get("nearest_neighbor_function_name_mangled", "N/A"),
                        "signature": match.get("signature", "N/A"),
                        "matched_binary": match.get("nearest_neighbor_binary_name", "N/A"),
                        "distance": distance,
                        "similarity": f"{similarity_percentage:.2f}%",
                        "confidence": f"{confidence_percentage:.2f}%",
                        "successful": "Yes" if is_successful else "No"
                    }
                    enriched_matches.append(enriched_match)
            
            log_info(f"RevEng.AI | Successfully matched {len(enriched_matches)} functions")
            return enriched_matches
            
        except Exception as e:
            log_error(f"RevEng.AI | Error matching functions: {str(e)}")
            raise e

    def get_function_details(self, bv: BinaryView, function_address: int) -> Optional[Dict]:
        """Get detailed information about a function"""
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
        
    def _parse_search_query(self, query):
        """
        Parse a search query with special selectors.

        Args:
            query (str): The search query string to parse

        Returns:
            dict: A dictionary containing parsed query components

        Raises:
            ValueError: If multiple non-tag selectors or a selector with raw
                        query are used
        """
        # Initialize the result dictionary with default empty values
        result = {
            'query': None,
            'sha_256_hash': None,
            'tags': None,
            'binary_name': None,
            'collection_name': None,
            'function_name': None,
            'model_name': None
        }

        # List of possible selectors (excluding 'tag')
        single_selectors = [
            'sha_256_hash',
            'binary_name',
            'collection_name',
            'function_name',
            'model_name'
        ]

        # Parse selector-based queries
        def extract_selector_value(query, selector):
            """Helper function to extract selector value"""
            selector_pattern = f"{selector}:"
            selector_match = query.find(selector_pattern)

            if selector_match != -1:
                # Extract the value after the selector
                start = selector_match + len(selector_pattern)
                end = query.find(' ', start)

                # If no space found, take till the end of string
                if end == -1:
                    end = len(query)

                # Extract the value and the full selector part
                value = query[start:end].strip()
                full_selector_part = query[selector_match:end].strip()

                return value, full_selector_part

            return None, None

        # Process tags first (can be multiple)
        def process_tags(query):
            tags = []
            while True:
                tag_value, tag_part = extract_selector_value(query, 'tag')
                if not tag_value:
                    break
                tags.append(tag_value)
                query = query.replace(tag_part, '').strip()
            if len(tags) == 0:
                tags = None
            return tags, query

        # Process tags
        result['tags'], query = process_tags(query)

        # Process other single selectors
        for selector in single_selectors:
            value, selector_part = extract_selector_value(query, selector)

            if value:
                # Check if this selector was already set
                if result[selector] is not None:
                    raise ValueError(
                        f"Only one {selector} selector can be used.")

                result[selector] = value
                query = query.replace(selector_part, '').strip()

        # Validation checks for additional text
        query = query.strip()
        if query:
            # If query is not empty after removing selectors
            if any(result[selector] is not None for selector in
                   single_selectors):
                raise ValueError(
                    "Selector cannot be used with additional text.")
            # If no other selectors, treat as raw query
            result['query'] = query

        return result