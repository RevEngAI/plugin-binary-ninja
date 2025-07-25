from datetime import datetime
from binaryninja import BinaryView, log_error, log_info, Symbol, SymbolType
from typing import List

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
