import pytest

pytest.importorskip("binaryninja")

from libbs.artifacts import Enum, Struct, Typedef, _art_from_dict

from reai_toolkit.utils.features import datatypes as dt_mod

PRIMITIVE_DATA_TYPES = {
    "1": {"data_type_id": 1, "kind": "BASE", "name": "int"},
    "2": {"data_type_id": 2, "kind": "BASE", "name": "char"},
}

STRUCT_DATA_TYPES = {
    "1": {"data_type_id": 1, "kind": "BASE", "name": "int"},
    "2": {
        "data_type_id": 2,
        "kind": "STRUCT",
        "name": "point_t",
        "size": 8,
        "definition": {
            "members": [
                {"name": "x", "offset": 0, "size": 4, "data_type_id": 1},
                {"name": "y", "offset": 4, "size": 4, "data_type_id": 1},
            ]
        },
    },
}

ENUM_DATA_TYPES = {
    "1": {"data_type_id": 1, "kind": "BASE", "name": "int"},
    "3": {
        "data_type_id": 3,
        "kind": "ENUM",
        "name": "color_t",
        "definition": {
            "values": [
                {"name": "RED", "value": "0"},
                {"name": "GREEN", "value": "1"},
            ]
        },
    },
}

TYPEDEF_OF_STRUCT_DATA_TYPES = {
    **STRUCT_DATA_TYPES,
    "4": {
        "data_type_id": 4,
        "kind": "TYPEDEF",
        "name": "point_ptr_t",
        "definition": {"target_data_type_id": 2},
    },
}


def test_build_signature_data_resolves_primitive_parameters_and_return_type():
    signature = {
        "function_id": 100,
        "function_name": "count_labels",
        "has_signature": True,
        "calling_convention": "cdecl",
        "parameters": [
            {"name": "count", "ordinal": 0, "data_type_id": 1},
            {"name": "label", "ordinal": 1, "data_type_id": 2},
        ],
        "return_data_type_id": 1,
        "source_function_id": 55,
        "source_type": "similar_function",
    }

    result = dt_mod.build_signature_data(signature, PRIMITIVE_DATA_TYPES)

    assert result is not None
    function = result["function"]
    assert function.name == "count_labels"
    assert function.type == "int"
    assert function.args[0].name == "count"
    assert function.args[0].type == "int"
    assert function.args[1].name == "label"
    assert function.args[1].type == "char"
    assert result["deps"] == []


def test_build_signature_data_returns_none_when_signature_unavailable():
    signature = {
        "function_id": 100,
        "has_signature": False,
        "parameters": [],
        "return_data_type_id": None,
    }

    assert dt_mod.build_signature_data(signature, {}) is None


def test_build_signature_data_includes_struct_dependency_for_struct_parameter():
    signature = {
        "function_id": 101,
        "function_name": "consume_point",
        "has_signature": True,
        "parameters": [{"name": "p", "ordinal": 0, "data_type_id": 2}],
        "return_data_type_id": 1,
    }

    result = dt_mod.build_signature_data(signature, STRUCT_DATA_TYPES)

    assert result["function"].args[0].type == "point_t"
    assert len(result["deps"]) == 1

    dependency = _art_from_dict(result["deps"][0])
    assert isinstance(dependency, Struct)
    assert dependency.name == "point_t"
    assert {member.name for member in dependency.members.values()} == {"x", "y"}


def test_build_signature_data_includes_enum_dependency_for_enum_return_type():
    signature = {
        "function_id": 102,
        "function_name": "current_color",
        "has_signature": True,
        "parameters": [],
        "return_data_type_id": 3,
    }

    result = dt_mod.build_signature_data(signature, ENUM_DATA_TYPES)

    assert result["function"].type == "color_t"
    assert len(result["deps"]) == 1

    dependency = _art_from_dict(result["deps"][0])
    assert isinstance(dependency, Enum)
    assert dependency.name == "color_t"
    assert dict(dependency.members) == {"RED": 0, "GREEN": 1}


def test_build_signature_data_recursively_resolves_typedef_of_struct():
    signature = {
        "function_id": 103,
        "function_name": "consume_point_ptr",
        "has_signature": True,
        "parameters": [{"name": "p", "ordinal": 0, "data_type_id": 4}],
        "return_data_type_id": 1,
    }

    result = dt_mod.build_signature_data(signature, TYPEDEF_OF_STRUCT_DATA_TYPES)

    assert result["function"].args[0].type == "point_ptr_t"

    dependencies = [_art_from_dict(dep) for dep in result["deps"]]
    assert {type(dependency) for dependency in dependencies} == {Typedef, Struct}

    typedef = next(d for d in dependencies if isinstance(d, Typedef))
    assert typedef.name == "point_ptr_t"
    assert typedef.type == "point_t"

    struct = next(d for d in dependencies if isinstance(d, Struct))
    assert struct.name == "point_t"


def test_build_signature_data_dedupes_shared_dependency():
    signature = {
        "function_id": 104,
        "function_name": "consume_two_points",
        "has_signature": True,
        "parameters": [
            {"name": "a", "ordinal": 0, "data_type_id": 2},
            {"name": "b", "ordinal": 1, "data_type_id": 2},
        ],
        "return_data_type_id": 1,
    }

    result = dt_mod.build_signature_data(signature, STRUCT_DATA_TYPES)

    assert len(result["deps"]) == 1
