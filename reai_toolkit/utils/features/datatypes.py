from libbs.artifacts import _art_from_dict, Function, FunctionArgument, FunctionHeader, GlobalVariable, Enum, Struct, Typedef
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


def _resolve_struct_dep(entry: dict, data_types: dict, deps_by_name: dict) -> None:
    name = entry.get("name")
    if name is None or name in deps_by_name:
        return

    # Registered before its members are resolved so a self-referential struct (e.g. a member
    # pointing back to its own type) terminates instead of recursing forever.
    deps_by_name[name] = {
        "artifact_type": "Struct",
        "name": name,
        "size": entry.get("size"),
        "members": {},
    }

    members = {}
    for member in (entry.get("definition") or {}).get("members") or []:
        member_type, _ = _resolve_type(
            member.get("data_type_id"), data_types, deps_by_name
        )
        members[hex(member["offset"])] = {
            "name": member.get("name"),
            "offset": member["offset"],
            "type": member_type,
            "size": member.get("size"),
        }
    deps_by_name[name]["members"] = members


def _resolve_enum_dep(entry: dict, deps_by_name: dict) -> None:
    name = entry.get("name")
    if name is None or name in deps_by_name:
        return

    deps_by_name[name] = {
        "artifact_type": "Enum",
        "name": name,
        "members": {
            value["name"]: int(value["value"])
            for value in (entry.get("definition") or {}).get("values") or []
        },
    }


def _resolve_typedef_dep(entry: dict, data_types: dict, deps_by_name: dict) -> None:
    name = entry.get("name")
    if name is None or name in deps_by_name:
        return

    deps_by_name[name] = {"artifact_type": "Typedef", "name": name, "type": None}
    base_type, _ = _resolve_type(
        (entry.get("definition") or {}).get("target_data_type_id"),
        data_types,
        deps_by_name,
    )
    deps_by_name[name]["type"] = base_type


def _resolve_type(data_type_id, data_types: dict, deps_by_name: dict) -> tuple:
    """Resolve a v3 data_type_id to its type name and size, registering any Struct/Enum/Typedef
    it (or a type it references) names as a dependency in deps_by_name."""
    if data_type_id is None:
        return None, None

    entry = data_types.get(str(data_type_id))
    if entry is None:
        return None, None

    kind = entry.get("kind")
    definition = entry.get("definition") or {}
    if kind in ("STRUCT", "UNION"):
        _resolve_struct_dep(entry, data_types, deps_by_name)
    elif kind == "ENUM":
        _resolve_enum_dep(entry, deps_by_name)
    elif kind == "TYPEDEF":
        _resolve_typedef_dep(entry, data_types, deps_by_name)
    elif kind == "POINTER":
        _resolve_type(definition.get("pointee_data_type_id"), data_types, deps_by_name)
    elif kind == "ARRAY":
        _resolve_type(definition.get("element_data_type_id"), data_types, deps_by_name)

    return entry.get("name"), entry.get("size")


def build_signature_data(signature: dict, data_types: dict) -> dict | None:
    """Convert a v3 BatchFunctionSignatureEntry into the libbs artifact graph apply_data_types
    applies. Returns None when the analysis holds no signature for this function."""
    if not signature.get("has_signature"):
        return None

    deps_by_name: dict = {}

    args = {}
    for parameter in signature.get("parameters") or []:
        arg_type, arg_size = _resolve_type(
            parameter.get("data_type_id"), data_types, deps_by_name
        )
        args[parameter["ordinal"]] = FunctionArgument(
            offset=parameter["ordinal"],
            name=parameter.get("name"),
            type_=arg_type,
            size=arg_size,
        )

    return_type, _ = _resolve_type(
        signature.get("return_data_type_id"), data_types, deps_by_name
    )

    function = Function(
        header=FunctionHeader(
            name=signature.get("function_name"),
            type_=return_type,
            args=args,
        )
    )

    return {"function": function, "deps": list(deps_by_name.values())}
