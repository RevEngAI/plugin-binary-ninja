from datetime import datetime
from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.choose_source import choose_source as mod


def test_get_analysis_lists_supported_models_only(mocker):
    mocker.patch.object(mod, "get_sha256", return_value="deadbeef")
    mocker.patch.object(mod, "AnalysisSyncService")
    api = mocker.patch.object(mod.revengai, "BinariesApi").return_value
    api.v3_search_binaries.return_value = MagicMock(
        results=[
            MagicMock(
                binary_name="a",
                binary_id=1,
                analysis_id=2,
                model_name="binnet-1.0",
                model_id=3,
                created_at=datetime(2026, 1, 1),
            )
        ]
    )

    config = MagicMock()
    config.filter_supported_models.return_value = []

    ok, _ = mod.ChooseSource(config).get_analysis(MagicMock())

    assert ok is False
    config.filter_supported_models.assert_called_once_with(
        api.v3_search_binaries.return_value.results
    )
