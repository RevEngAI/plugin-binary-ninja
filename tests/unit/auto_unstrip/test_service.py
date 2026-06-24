from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.auto_unstrip import auto_unstrip as au_mod


def _match(vaddr, suggested_demangled, suggested, function_id):
    match = MagicMock()
    match.function_vaddr = vaddr
    match.suggested_demangled_name = suggested_demangled
    match.suggested_name = suggested
    match.function_id = function_id
    return match


@pytest.fixture
def feature():
    config = MagicMock()
    config.get_analysis_id.return_value = 7
    return au_mod.AutoUnstrip(config)


@pytest.fixture
def api(mocker):
    inst = mocker.patch.object(au_mod.revengai, "FunctionsCoreApi").return_value
    return inst


def test_auto_unstrip_maps_completed_matches(feature, api, mocker):
    api.auto_unstrip.return_value = MagicMock(
        status="completed",
        matches=[_match(0x1000, "foo", "_Z3foov", 42)],
    )
    func = MagicMock()
    func.name = "sub_1000"
    mocker.patch.object(au_mod, "get_function_by_addr_util", return_value=func)

    ok, results = feature.auto_unstrip(MagicMock())

    assert ok is True
    assert results == [
        {
            "virtual_address": 0x1000,
            "current_name": "sub_1000",
            "suggested_name": "foo",
            "suggested_mangled_name": "_Z3foov",
            "source_function_id": 42,
        }
    ]


def test_auto_unstrip_handles_missing_local_function(feature, api, mocker):
    api.auto_unstrip.return_value = MagicMock(
        status="completed",
        matches=[_match(0x2000, "bar", "_Z3barv", 99)],
    )
    mocker.patch.object(
        au_mod, "get_function_by_addr_util", side_effect=Exception("not found")
    )

    ok, results = feature.auto_unstrip(MagicMock())

    assert ok is True
    assert results[0]["current_name"] == "N/A"
    assert results[0]["suggested_name"] == "bar"


def test_auto_unstrip_polls_until_completed(feature, api, mocker):
    api.auto_unstrip.side_effect = [
        MagicMock(status="processing"),
        MagicMock(status="completed", matches=[]),
    ]
    mocker.patch.object(au_mod.time, "sleep")

    ok, results = feature.auto_unstrip(MagicMock())

    assert ok is True
    assert results == []
    assert api.auto_unstrip.call_count == 2
