from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

import revengai

from reai_toolkit.utils.core import binary_ninja as bn_mod


def test_get_function_id_by_addr_uses_list_analysis_functions(mocker):
    config = MagicMock()
    config.get_analysis_id.return_value = 42
    old_api = mocker.patch.object(revengai, "AnalysesResultsMetadataApi").return_value
    old_api.get_functions_list.side_effect = AssertionError(
        "get_function_id_by_addr must look up functions via "
        "FunctionsCoreApi.list_analysis_functions, not the retired "
        "AnalysesResultsMetadataApi.get_functions_list"
    )
    functions_api = mocker.patch.object(revengai, "FunctionsCoreApi").return_value
    entry = MagicMock(function_vaddr=0x1000, function_id=7)
    functions_api.list_analysis_functions.return_value.functions = [entry]
    bv = MagicMock()

    function_id = bn_mod.get_function_id_by_addr(bv, 0x1000, config)

    functions_api.list_analysis_functions.assert_called_once_with(analysis_id=42)
    assert function_id == 7


def test_get_function_id_by_addr_raises_when_address_not_found(mocker):
    config = MagicMock()
    config.get_analysis_id.return_value = 42
    old_api = mocker.patch.object(revengai, "AnalysesResultsMetadataApi").return_value
    old_api.get_functions_list.return_value.data.functions = []
    functions_api = mocker.patch.object(revengai, "FunctionsCoreApi").return_value
    functions_api.list_analysis_functions.return_value.functions = []
    bv = MagicMock()

    with pytest.raises(Exception, match="Function not found at address"):
        bn_mod.get_function_id_by_addr(bv, 0x1000, config)


def test_rename_in_portal_uses_rename_function(mocker):
    config = MagicMock()
    renaming_api = mocker.patch.object(
        revengai, "FunctionsRenamingHistoryApi"
    ).return_value

    bn_mod._rename_in_portal(config, 7, "new_name", "new_mangled_name")

    renaming_api.rename_function.assert_called_once()
    call_kwargs = renaming_api.rename_function.call_args.kwargs
    assert call_kwargs["function_id"] == 7
    body = call_kwargs["rename_input_body"]
    assert isinstance(body, revengai.RenameInputBody)
    assert body.new_name == "new_name"
    assert body.new_mangled_name == "new_mangled_name"
