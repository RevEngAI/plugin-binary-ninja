from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

import revengai

from reai_toolkit.features.view_function_in_portal import (
    view_function_in_portal as vfp_mod,
)


def test_view_function_in_portal_uses_list_analysis_functions(mocker):
    config = MagicMock()
    config.get_analysis_id.return_value = 42
    config.portal_url = "https://portal.reveng.ai"

    old_api = mocker.patch.object(revengai, "AnalysesResultsMetadataApi").return_value
    old_api.get_functions_list.side_effect = AssertionError(
        "view_function_in_portal must look up functions via "
        "FunctionsCoreApi.list_analysis_functions, not the retired "
        "AnalysesResultsMetadataApi.get_functions_list"
    )
    functions_api = mocker.patch.object(revengai, "FunctionsCoreApi").return_value
    entry = MagicMock(function_vaddr=0x2000, function_id=99)
    functions_api.list_analysis_functions.return_value.functions = [entry]

    interaction_cls = mocker.patch.object(vfp_mod, "InteractionHandler")

    bv = MagicMock()
    target_function = MagicMock(start=0x2000)
    bv.get_functions_containing.return_value = [target_function]

    feature = vfp_mod.ViewFunctionInPortal(config)
    ok, _ = feature.view_function_in_portal(bv, {"function": 0x2000})

    functions_api.list_analysis_functions.assert_called_once()
    call = functions_api.list_analysis_functions.call_args
    assert 42 in call.args or call.kwargs.get("analysis_id") == 42
    assert ok is True
    interaction_cls.return_value.open_url.assert_called_once_with(
        "https://portal.reveng.ai/analyses/42?fn=99&view=matching&matchingMode=single"
    )
