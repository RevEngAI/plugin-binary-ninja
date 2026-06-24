from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.headless
pytest.importorskip("binaryninja")

from reai_toolkit.utils.core import sync as sync_mod


def test_sync_renames_matched_function_in_binary(bv):
    target = next(
        (f for f in bv.functions if not (f.symbol and f.symbol.auto is False)), None
    )
    if target is None:
        pytest.skip("no auto-named function available to rename")
    start = target.start

    func_map = MagicMock()
    func_map.function_map = {"1": start}
    func_map.inverse_function_map = {str(start): 1}
    func_map.name_map = {str(start): "renamed_by_reveng"}

    sync_mod.AnalysisSyncService(MagicMock())._match_functions(func_map=func_map, bv=bv)

    assert bv.get_function_at(start).name == "renamed_by_reveng"


def test_sync_skips_user_named_function(bv):
    from binaryninja import Symbol, SymbolType

    start = next(iter(bv.functions)).start
    bv.define_user_symbol(Symbol(SymbolType.FunctionSymbol, start, "user_named"))

    func_map = MagicMock()
    func_map.function_map = {"1": start}
    func_map.inverse_function_map = {str(start): 1}
    func_map.name_map = {str(start): "should_not_apply"}

    sync_mod.AnalysisSyncService(MagicMock())._match_functions(func_map=func_map, bv=bv)

    assert bv.get_function_at(start).name == "user_named"


def test_rebase_returns_view_at_analysis_base(bv, mocker):
    service = sync_mod.AnalysisSyncService(MagicMock())
    mocker.patch.object(sync_mod, "ApiClient")
    api = mocker.patch.object(sync_mod, "AnalysesCoreApi").return_value
    target = bv.start + 0x100000
    api.get_analysis_basic_info.return_value.data.base_address = target

    rebased = service._fetch_basic_and_rebase(bv, analysis_id=1)

    assert rebased.start == target
    assert rebased is not bv


def test_rebase_skipped_when_already_aligned(bv, mocker):
    service = sync_mod.AnalysisSyncService(MagicMock())
    mocker.patch.object(sync_mod, "ApiClient")
    api = mocker.patch.object(sync_mod, "AnalysesCoreApi").return_value
    api.get_analysis_basic_info.return_value.data.base_address = bv.start

    result = service._fetch_basic_and_rebase(bv, analysis_id=1)

    assert result is bv
