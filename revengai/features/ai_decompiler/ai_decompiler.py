from binaryninja import BinaryView, log_info, log_error, Symbol, SymbolType, interaction
from binaryninja.interaction import InteractionHandler
from reait.api import RE_authentication, RE_search, RE_nearest_symbols_batch, RE_analyze_functions, RE_name_score, RE_functions_data_types, RE_functions_data_types_poll, RE_get_analysis_id_from_binary_id, RE_get_functions_from_analysis
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple
import math
from revengai.utils.datatypes import apply_data_types as apply_data_types_util
import time
from revengai.utils import rename_function as rename_function_util
from libbs.api import DecompilerInterface
from libbs.decompilers.binja.interface import BinjaInterface
from libbs.artifacts import _art_from_dict
from libbs.artifacts import (
    Function,
    FunctionArgument,
    GlobalVariable,
    Enum,
    Struct,
    Typedef,
)

class AIDecompiler:
    def __init__(self, config):
        self.config = config


    def get_ai_decompiler(self, bv: BinaryView, options: Dict) -> None:
        """Match functions from the binary against RevEng.AI database"""
        try:
            log_info("RevEng.AI | Starting function searching in portal")
            function_addr = options.get("function", None)

            functions_containing = bv.get_functions_containing(function_addr)
            
            if not functions_containing:
                log_error(f"RevEng.AI | Function not found at 0x{function_addr:x}")
                raise Exception("Function not found at address")
            
            function = functions_containing[0]
            log_info(f"RevEng.AI | Function: {function.name} at 0x{function.start:x} (Clicked address: 0x{function_addr:x})")

            binary_id = self.config.get_binary_id(bv)
            if not binary_id:
                raise Exception("Analysis not found. Please choose one using 'Choose Source' feature.")
            
            analysis = RE_get_analysis_id_from_binary_id(binary_id).json()
            analyzed_functions = RE_get_functions_from_analysis(analysis["analysis_id"]).json()["data"]["functions"]

            analyzed_function = next((f for f in analyzed_functions if (f["function_vaddr"] + bv.image_base) == function.start), None)
            if not analyzed_function:
                log_error(f"RevEng.AI | Function {function.name} not found in analyzed functions")
                raise Exception("Function not found in analyzed functions")
            
            url = f"https://portal.reveng.ai/function/{analyzed_function['function_id']}"
            InteractionHandler().open_url(url)

            return True, "Function found in portal"

        except Exception as e:
            log_error(f"RevEng.AI | Error in function matching: {str(e)}")
            return False, str(e)