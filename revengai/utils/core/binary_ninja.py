from datetime import datetime
from binaryninja import BinaryView, log_error, log_info, Symbol, SymbolType, Function
from reait.api import RE_analyze_functions

def rename_function(bv: BinaryView, addr: int, new_name: str, data_type: dict = None) -> bool:
    try:
        func = bv.get_function_at(addr)
        if not func:
            log_error(f"RevEng.AI | No function found at address {hex(addr)}")
            return False
        
        if func.name == new_name:
            log_info(f"RevEng.AI | Function at {hex(addr)} already has name {func.name}")
            #return False
        
        new_symbol = Symbol(SymbolType.FunctionSymbol, addr, new_name)
        bv.define_user_symbol(new_symbol)
        
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
        log_error(f"RevEng.AI | Function not found at 0x{addr:x}")
        raise Exception("Function not found at address")
    
    return functions_containing[0]

def get_function_id_by_addr(bv: BinaryView, addr: int, binary_id: int):
    analyzed_functions = RE_analyze_functions(bv.file.filename, binary_id).json()["functions"]
    target_function = next((f for f in analyzed_functions if (f["function_vaddr"] + bv.image_base) == addr), None)
    if not target_function:
        log_error(f"RevEng.AI | Function not found at 0x{addr:x}")
        raise Exception("Function not found at address")
    function_id = target_function["function_id"]
    log_info(f"RevEng.AI | Found function id {function_id} for function at 0x{addr:x}")
    return function_id