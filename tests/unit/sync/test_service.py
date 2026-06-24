from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.utils.core import sync as sync_mod


def _func(start, auto=True, name="sub_1000"):
    func = MagicMock()
    func.start = start
    func.name = name
    func.symbol.auto = auto
    return func


def _func_map(start, function_id=5, new_name="real_name"):
    func_map = MagicMock()
    func_map.function_map = {str(function_id): start}
    func_map.inverse_function_map = {str(start): function_id}
    func_map.name_map = {str(start): new_name}
    return func_map


def test_match_functions_renames_auto_named_function(mocker):
    service = sync_mod.AnalysisSyncService(MagicMock())
    bv = MagicMock()
    bv.functions = [_func(0x1000, auto=True)]
    symbol = mocker.patch.object(sync_mod, "Symbol")

    service._match_functions(func_map=_func_map(0x1000), bv=bv)

    symbol.assert_called_once_with(
        sync_mod.SymbolType.FunctionSymbol, 0x1000, "real_name"
    )
    bv.define_user_symbol.assert_called_once_with(symbol.return_value)


def test_match_functions_skips_user_defined_function(mocker):
    service = sync_mod.AnalysisSyncService(MagicMock())
    bv = MagicMock()
    bv.functions = [_func(0x1000, auto=False)]
    mocker.patch.object(sync_mod, "Symbol")

    service._match_functions(func_map=_func_map(0x1000), bv=bv)

    bv.define_user_symbol.assert_not_called()


def test_fetch_basic_and_rebase_rebases_on_delta(mocker):
    service = sync_mod.AnalysisSyncService(MagicMock())
    mocker.patch.object(sync_mod, "ApiClient")
    api = mocker.patch.object(sync_mod, "AnalysesCoreApi").return_value
    api.get_analysis_basic_info.return_value.data.base_address = 0x400000
    bv = MagicMock()
    bv.start = 0x0

    service._fetch_basic_and_rebase(bv, analysis_id=7)

    bv.rebase.assert_called_once_with(0x400000)


def test_fetch_basic_and_rebase_noop_when_aligned(mocker):
    service = sync_mod.AnalysisSyncService(MagicMock())
    mocker.patch.object(sync_mod, "ApiClient")
    api = mocker.patch.object(sync_mod, "AnalysesCoreApi").return_value
    api.get_analysis_basic_info.return_value.data.base_address = 0x400000
    bv = MagicMock()
    bv.start = 0x400000

    service._fetch_basic_and_rebase(bv, analysis_id=7)

    bv.rebase.assert_not_called()
