from datetime import datetime
from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

import revengai

from reai_toolkit.features.match_functions import match_functions as mf_mod


def test_process_rename_batch_counts_successful_renames(mocker):
    feature = mf_mod.MatchFunctions(MagicMock())
    rename = mocker.patch.object(mf_mod, "rename_function_util", return_value=True)
    chunk = [
        {
            "function_address": "4096",
            "matched_function_name": "foo",
            "matched_mangled_name": "_Z3foov",
            "source_function_id": 7,
        }
    ]

    renamed, datatypes = feature._process_rename_batch(MagicMock(), chunk, MagicMock())

    assert renamed == 1
    assert datatypes == 0
    args = rename.call_args[0]
    assert args[2] == 4096
    assert args[3] == "foo"


def test_process_rename_batch_skips_invalid_address(mocker):
    feature = mf_mod.MatchFunctions(MagicMock())
    mocker.patch.object(mf_mod, "rename_function_util", return_value=True)
    chunk = [
        {
            "function_address": "not-an-int",
            "matched_function_name": "x",
            "matched_mangled_name": "y",
            "source_function_id": 1,
        }
    ]

    renamed, _ = feature._process_rename_batch(MagicMock(), chunk, MagicMock())

    assert renamed == 0


def test_match_functions_lists_analyzed_functions_via_list_analysis_functions(mocker):
    mocker.patch("time.sleep")
    config = MagicMock()
    config.get_analysis_id.return_value = 42

    old_api = mocker.patch.object(revengai, "AnalysesResultsMetadataApi").return_value
    old_api.get_functions_list.side_effect = AssertionError(
        "match_functions must list analyzed functions via "
        "FunctionsCoreApi.list_analysis_functions, not the retired "
        "AnalysesResultsMetadataApi.get_functions_list"
    )

    entries = [{"function_id": 7, "function_vaddr": 0x1000, "function_name": "foo"}]
    functions_api = mocker.patch.object(revengai, "FunctionsCoreApi").return_value
    functions_api.list_analysis_functions.return_value.functions = entries
    functions_api.list_analysis_functions.return_value.to_dict.return_value = {
        "functions": entries
    }

    core_api = mocker.patch.object(revengai, "AnalysesCoreApi").return_value
    status = MagicMock(step_index=1, steps_total=1)
    status.status = revengai.BinaryTaskStatus.COMPLETED
    core_api.get_analysis_function_matching_status.return_value = status
    core_api.get_analysis_function_matches.return_value = MagicMock(matches=[])

    bv = MagicMock()
    matched_function = MagicMock(start=0x1000)
    bv.functions = [matched_function]

    feature = mf_mod.MatchFunctions(config)
    ok, result = feature.match_functions(bv, {})

    functions_api.list_analysis_functions.assert_called_once()
    call = functions_api.list_analysis_functions.call_args
    assert 42 in call.args or call.kwargs.get("analysis_id") == 42
    assert ok is True
    assert result["skipped"] == 0


def test_search_binaries_uses_v3_binaries_endpoint(mocker):
    config = MagicMock()

    old_api = mocker.patch.object(revengai, "SearchApi").return_value
    old_api.search_binaries.side_effect = AssertionError(
        "binary search must go through BinariesApi.v3_search_binaries, not the "
        "deprecated SearchApi.search_binaries"
    )

    created_at = datetime(2024, 5, 1, 12, 30)
    binaries_api = mocker.patch.object(revengai, "BinariesApi").return_value
    binaries_api.v3_search_binaries.return_value = MagicMock(
        results=[
            MagicMock(
                binary_name="libc.so",
                binary_id=11,
                analysis_id=22,
                sha_256_hash="abc",
                owned_by="someone",
                created_at=created_at,
            )
        ]
    )

    feature = mf_mod.MatchFunctions(config)
    items = feature._search_binaries({"binary_name": "libc"})

    call = binaries_api.v3_search_binaries.call_args
    assert call.kwargs["limit"] == 20
    assert call.kwargs["offset"] == 0
    assert "page" not in call.kwargs and "page_size" not in call.kwargs
    assert items == [
        {
            "name": "libc.so",
            "binary_id": "11",
            "analysis_id": "22",
            "sha_256_hash": "abc",
            "owner": "someone",
            "date": created_at.strftime("%m/%d/%Y %H:%M"),
        }
    ]
