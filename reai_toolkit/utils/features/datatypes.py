from libbs.artifacts import _art_from_dict, Function, GlobalVariable, Enum, Struct, Typedef
from libbs.api import DecompilerInterface
from binaryninja import log_error, log_info
from typing import List   

def apply_type(deci: DecompilerInterface, artifact, soft_skip=False) -> None | str:
        supported_types = [
            Function,
            GlobalVariable,
            Enum,
            Struct,
            Typedef
        ]

        if not any(isinstance(artifact, t) for t in supported_types):
            return "Unsupported artifact type: " \
                f"{artifact.__class__.__name__}"

        # Validate artifact before applying
        try:
            

            # Apply the artifact
            if isinstance(artifact, Function):
                deci.functions[artifact.addr] = artifact
            elif isinstance(artifact, GlobalVariable):
                deci.global_vars[artifact.addr] = artifact
            elif isinstance(artifact, Enum):
                deci.enums[artifact.name] = artifact
            elif isinstance(artifact, Struct):
                deci.structs[artifact.name] = artifact
            elif isinstance(artifact, Typedef):
                deci.typedefs[artifact.name] = artifact

        except Exception as e:
            error_msg = f"Error while applying artifact '{getattr(artifact, 'name', 'unnamed')}'" \
                       f" of type {artifact.__class__.__name__}: {e}"
            log_error(f"RevEng.AI | {error_msg}")
            if not soft_skip:
                return error_msg

        return None
        
def apply_types(deci: DecompilerInterface, artifacts: List) -> None | str:
        if not artifacts:
            log_info("RevEng.AI | No artifacts to apply")
            return None
            
        failed_count = 0
        success_count = 0
        
        for artifact in artifacts:
            try:
                error = apply_type(deci, artifact, True)
                if error is not None:
                    failed_count += 1
                    log_info(f"RevEng.AI | Failed to apply artifact: {error}")
                else:
                    success_count += 1
            except Exception as e:
                failed_count += 1
                artifact_name = getattr(artifact, 'name', 'unnamed')
                log_error(f"RevEng.AI | Exception applying artifact '{artifact_name}': {e}")
        
        log_info(f"RevEng.AI | Applied {success_count} artifacts, {failed_count} failed")
        
        # Only return error if ALL artifacts failed
        if failed_count > 0 and success_count == 0:
            return f"All {failed_count} artifacts failed to apply"
        
        return None
    
def load_many_artifacts_from_list(artifacts: list[dict]) -> list:
    _artifacts = []
    for artifact in artifacts:
        try:
            art = _art_from_dict(artifact)
            if art is not None:
                _artifacts.append(art)
        except Exception as e:
            log_error(f"RevEng.AI | Error loading artifact: {e}")
            continue
    return _artifacts
        
def apply_data_types(function_addr: int = 0, signature=None, deci: DecompilerInterface = None) -> None:
        if not deci:
            log_error("RevEng.AI | Unable to find a decompiler")
            return

        try:
            function: Function = signature.get("function")
            deps = signature.get("deps")

            if not function:
                log_error("RevEng.AI | No function signature found")
                return

            function.addr = function_addr

            valid_deps = load_many_artifacts_from_list(deps)

            log_info(f"RevEng.AI | Applying {len(valid_deps)} dependencies")
            if valid_deps:
                res = apply_types(deci, valid_deps)
                if res is not None:
                    log_error(f"RevEng.AI | Failed to apply function dependencies: {res}")
                    return

            log_info(f"RevEng.AI | Applying function signature for {function.name}")
            res = apply_type(deci, function)
            if res is not None:
                log_error(f"RevEng.AI | Failed to apply function signature: {res}")
                return

            log_info("RevEng.AI | Successfully applied function signature and dependencies")

        except Exception as e:
            log_info(f"RevEng.AI | Error in _apply_data_types: {e}")