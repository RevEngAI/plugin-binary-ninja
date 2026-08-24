from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

import revengai

from reai_toolkit.features.match_current_function import (
    match_current_function as mcf_mod,
)


def test_match_current_function_lists_analyzed_functions_via_list_analysis_functions(
    mocker,
):
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
    status = MagicMock(step_index=1, steps_total=1)
    status.status = revengai.TaskStatus.COMPLETED
    functions_api.get_functions_matching_status.return_value = status
    functions_api.get_functions_matches.return_value = MagicMock(matches=[])

    bv = MagicMock()
    target_function = MagicMock(start=0x1000, name="foo")
    bv.get_functions_containing.return_value = [target_function]

    feature = mcf_mod.MatchCurrentFunction(config)
    ok, result = feature.match_functions(bv, {"function": 0x1000})

    functions_api.list_analysis_functions.assert_called_once()
    call = functions_api.list_analysis_functions.call_args
    assert 42 in call.args or call.kwargs.get("analysis_id") == 42
    assert ok is True
