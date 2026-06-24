from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.headless
pytest.importorskip("binaryninja")

from reai_toolkit.utils.core import binary_ninja as bn_mod


def test_rename_function_applies_user_symbol(bv, mocker):
    target = next(
        (f for f in bv.functions if not (f.symbol and f.symbol.auto is False)), None
    )
    if target is None:
        pytest.skip("no auto-named function available to rename")
    addr = target.start
    portal = mocker.patch.object(bn_mod, "_rename_in_portal")

    ok = bn_mod.rename_function(
        MagicMock(), bv, addr, "demangled_name", "mangled_name", source_function_id=9
    )

    assert ok is True
    assert bv.get_function_at(addr).name == "mangled_name"
    portal.assert_called_once_with(mocker.ANY, 9, "demangled_name", "mangled_name")


def test_get_function_by_addr_resolves_real_function(bv):
    func = next(iter(bv.functions))

    resolved = bn_mod.get_function_by_addr(bv, func.start)

    assert resolved.start == func.start
