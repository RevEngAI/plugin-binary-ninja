from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.headless
pytest.importorskip("binaryninja")

from reai_toolkit.features.match_functions import match_functions as mf_mod
from reai_toolkit.utils.core import binary_ninja as bn_mod


def test_rename_functions_applies_via_binja_interface(bv, mocker):
    target = next(
        (f for f in bv.functions if not (f.symbol and f.symbol.auto is False)), None
    )
    if target is None:
        pytest.skip("no auto-named function available to rename")
    addr = target.start
    portal = mocker.patch.object(bn_mod, "_rename_in_portal")
    feature = mf_mod.MatchFunctions(MagicMock())

    ok, _ = feature.rename_functions(
        bv,
        [
            {
                "function_address": addr,
                "matched_function_name": "demangled",
                "matched_mangled_name": "mangled_applied",
                "source_function_id": 11,
            }
        ],
    )

    assert ok is True
    assert bv.get_function_at(addr).name == "mangled_applied"
    portal.assert_called_once()
