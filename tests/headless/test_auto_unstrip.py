from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.headless
pytest.importorskip("binaryninja")

from reai_toolkit.features.auto_unstrip import auto_unstrip as au_mod
from reai_toolkit.utils.core import binary_ninja as bn_mod


def test_auto_unstrip_maps_real_function_names(bv, mocker):
    func = next(iter(bv.functions))
    config = MagicMock()
    config.get_analysis_id.return_value = 1
    feature = au_mod.AutoUnstrip(config)

    match = MagicMock()
    match.function_vaddr = func.start
    match.suggested_demangled_name = "recovered"
    match.suggested_name = "_Z9recoveredv"
    match.function_id = 7
    api = mocker.patch.object(au_mod.revengai, "FunctionsCoreApi").return_value
    api.auto_unstrip.return_value = MagicMock(status="completed", matches=[match])

    ok, results = feature.auto_unstrip(bv)

    assert ok is True
    assert results[0]["virtual_address"] == func.start
    assert results[0]["current_name"] == func.name
    assert results[0]["suggested_name"] == "recovered"
    assert results[0]["source_function_id"] == 7


def test_auto_unstrip_rename_applies_symbol_to_real_function(bv, mocker):
    target = next(
        (f for f in bv.functions if not (f.symbol and f.symbol.auto is False)), None
    )
    if target is None:
        pytest.skip("no auto-named function available to rename")
    addr = target.start
    portal = mocker.patch.object(bn_mod, "_rename_in_portal")
    feature = au_mod.AutoUnstrip(MagicMock())

    ok, _ = feature.rename_functions(
        bv,
        [
            {
                "virtual_address": addr,
                "suggested_name": "demangled_x",
                "suggested_mangled_name": "mangled_x",
                "source_function_id": 3,
            }
        ],
    )

    assert ok is True
    assert bv.get_function_at(addr).name == "mangled_x"
    portal.assert_called_once()
