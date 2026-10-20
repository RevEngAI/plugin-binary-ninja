from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.headless
pytest.importorskip("binaryninja")

from reai_toolkit.features.upload import upload as upload_mod


def test_upload_binary_collects_real_function_boundaries(bv, mocker):
    uploader = upload_mod.BinaryUploader(MagicMock())
    api = mocker.patch.object(upload_mod.revengai, "AnalysesCoreApi").return_value
    api.upload_file.return_value.data.sha_256_hash = "abcd"
    api.create_analysis.return_value.data.analysis_id = 1
    api.create_analysis.return_value.data.binary_id = 2
    mocker.patch.object(upload_mod, "PeriodicChecker")

    ok, _ = uploader.upload_binary(
        bv, {"debug_info": None, "tags": ["unit-test"], "is_private": True}
    )

    assert ok is True
    request = api.create_analysis.call_args.kwargs["analysis_create_request"]
    payload = request.to_dict()
    symbols = payload["symbols"]
    real_starts = {f.start for f in bv.functions}
    assert symbols["base_address"] == bv.image_base
    assert {b["start_address"] for b in symbols["function_boundaries"]} == real_starts
    assert payload["analysis_scope"] == upload_mod.revengai.AnalysisScope.PRIVATE
    assert payload["tags"] == [{"name": "unit-test"}]
