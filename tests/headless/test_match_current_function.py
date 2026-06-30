from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.headless
pytest.importorskip("binaryninja")

from reai_toolkit.features.match_current_function import (
    match_current_function as mcf_mod,
)


def test_match_current_function_pipeline(bv, mocker):
    func = next(iter(bv.functions))
    config = MagicMock()
    config.get_analysis_id.return_value = 1
    config.model_id = 5
    feature = mcf_mod.MatchCurrentFunction(config)
    mocker.patch.object(mcf_mod.time, "sleep")

    meta_api = mocker.patch.object(
        mcf_mod.revengai, "AnalysesResultsMetadataApi"
    ).return_value
    meta_api.get_functions_list.return_value.to_dict.return_value = {
        "data": {
            "functions": [
                {
                    "function_id": 100,
                    "function_vaddr": func.start,
                    "function_name": func.name,
                }
            ]
        }
    }

    matched = MagicMock()
    matched.function_name = "match_name"
    matched.mangled_name = "_Z10match_namev"
    matched.sha_256_hash = "hash"
    matched.binary_name = "libc.so"
    matched.similarity = 95.0
    matched.confidence = 95.0
    matched.function_id = 200
    by_distance = MagicMock()
    by_distance.function_id = 100
    by_distance.matched_functions = [matched]
    core_api = mocker.patch.object(mcf_mod.revengai, "FunctionsCoreApi").return_value
    core_api.get_functions_matching_status.return_value = MagicMock(
        status="COMPLETED", step_index=1, steps_total=1
    )
    core_api.get_functions_matches.return_value = MagicMock(matches=[by_distance])

    ok, result = feature.match_functions(
        bv, {"function": func.start, "similarity_threshold": 90}
    )

    assert ok is True
    row = result["data"][0]
    assert row["function_address"] == func.start
    assert row["matched_function_name"] == "match_name"
    assert row["icon_text"] == "Success"
    assert result["matched"] == 1
