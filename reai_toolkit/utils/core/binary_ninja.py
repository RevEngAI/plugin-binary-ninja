from datetime import datetime
from binaryninja import BinaryView, log_error, log_info, Symbol, SymbolType, Function
import revengai
from hashlib import sha256
from os.path import isfile
from os import access, R_OK


def _rename_in_portal(config: revengai.Configuration, function_id:int, new_name:str, new_mangled_name:str):
    try:
        with config.create_api_client() as api_client:
            api_instance = revengai.FunctionsRenamingHistoryApi(api_client)
            api_instance.rename_function_id(
                function_id=function_id,
                function_rename=revengai.FunctionRename(
                    new_name=new_name,
                    new_mangled_name=new_mangled_name
                )
            )
            log_info(f"RevEng.AI | Renamed function in portal at {function_id} to {new_name}")

    except Exception as e:
        log_error(f"RevEng.AI | Error renaming function in portal at {function_id}: {str(e)}")

def rename_function(config, bv: BinaryView, addr: int, new_name: str, new_mangled_name: str, source_function_id: int, data_type: dict = None) -> bool:
    try:
        func = bv.get_function_at(addr)
        if not func:
            log_error(f"RevEng.AI | No function found at address {hex(addr)}")
            addr = addr + bv.image_base
            func = bv.get_function_at(addr)
            if not func:
                log_error(f"RevEng.AI | No function found at address {hex(addr)}")
                return False

        if func.name == new_name:
            log_info(f"RevEng.AI | Function at {hex(addr)} already has name {func.name}")
            #return False
        
        new_symbol = Symbol(SymbolType.FunctionSymbol, addr, new_mangled_name)
        bv.define_user_symbol(new_symbol)

        _rename_in_portal(config, source_function_id, new_name, new_mangled_name)
        
        log_info(f"RevEng.AI | Renamed function at {hex(addr)} to {new_name}")
        return True

    except Exception as e:
        log_error(f"RevEng.AI | Error renaming function at {hex(addr)}: {str(e)}")
        return False

def parse_date(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        return date_str

def get_function_by_addr(bv: BinaryView, addr: int) -> Function:
    functions_containing = bv.get_functions_containing(addr)
            
    if not functions_containing:
        log_error(f"RevEng.AI | Function not found at 0x{addr:x} searching with image base...")
        base_addr = bv.image_base
        new_addr = addr + base_addr
        functions_containing = bv.get_functions_containing(new_addr)
        if not functions_containing:
            log_error(f"RevEng.AI | Function not found at 0x{new_addr:x}")
            raise Exception("Function not found at address")
    
    return functions_containing[0]

def get_function_id_by_addr(bv: BinaryView, addr: int, config):
    with config.create_api_client() as api_client:
        api_instance = revengai.AnalysesResultsMetadataApi(api_client)
        analysis_id = config.get_analysis_id(bv)
        api_response = api_instance.get_functions_list(analysis_id)
        analyzed_functions = api_response.data.functions
        target_function = next((f for f in analyzed_functions if f.function_vaddr == addr), None)
        if not target_function:
            log_error(f"RevEng.AI | Function not found at 0x{addr:x}")
            raise Exception("Function not found at address")
        function_id = target_function.function_id
        log_info(f"RevEng.AI | Found function id {function_id} for function at 0x{addr:x}")
        return function_id

def get_sha256(filename):
    if filename and isfile(filename) and access(filename, R_OK):
        hf = sha256()
        with open(filename, "rb") as fd:
            c = fd.read()
            hf.update(c)
        return hf.hexdigest()
    else:
        raise Exception("SHA256 hash not found")