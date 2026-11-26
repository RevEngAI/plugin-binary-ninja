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
    functions_api.list_analysis_functions.return_value.total_count = 1
    bv = MagicMock()

    function_id = bn_mod.get_function_id_by_addr(bv, 0x1000, config)

    functions_api.list_analysis_functions.assert_called_once_with(analysis_id=42, offset=0, limit=500)
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


def _paged(functions_api, entries, page_size):
    def list_analysis_functions(analysis_id, offset=0, limit=100):
        page = MagicMock(total_count=len(entries))
        page.functions = entries[offset : offset + min(limit, page_size)]
        return page

    functions_api.list_analysis_functions.side_effect = list_analysis_functions


def test_list_all_analysis_functions_pages_until_total_count():
    functions_api = MagicMock()
    entries = [MagicMock(function_vaddr=i, function_id=i) for i in range(1200)]
    _paged(functions_api, entries, page_size=500)

    result = bn_mod.list_all_analysis_functions(functions_api, 42)

    assert result == entries
    assert [c.kwargs for c in functions_api.list_analysis_functions.call_args_list] == [
        {"analysis_id": 42, "offset": 0, "limit": 500},
        {"analysis_id": 42, "offset": 500, "limit": 500},
        {"analysis_id": 42, "offset": 1000, "limit": 500},
    ]


def test_list_all_analysis_functions_stops_on_empty_page():
    functions_api = MagicMock()
    page = MagicMock(total_count=10, functions=[])
    functions_api.list_analysis_functions.return_value = page

    assert bn_mod.list_all_analysis_functions(functions_api, 42) == []
    functions_api.list_analysis_functions.assert_called_once()


def test_get_function_id_by_addr_finds_function_beyond_first_page(mocker):
    config = MagicMock()
    config.get_analysis_id.return_value = 42
    functions_api = mocker.patch.object(revengai, "FunctionsCoreApi").return_value
    entries = [MagicMock(function_vaddr=i, function_id=i + 1) for i in range(150)]
    _paged(functions_api, entries, page_size=100)

    assert bn_mod.get_function_id_by_addr(MagicMock(), 120, config) == 121
