from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.match_functions import match_functions as mf_mod


def test_process_rename_batch_counts_successful_renames(mocker):
    feature = mf_mod.MatchFunctions(MagicMock())
    rename = mocker.patch.object(mf_mod, "rename_function_util", return_value=True)
    chunk = [
        {
            "function_address": "4096",
            "matched_function_name": "foo",
            "matched_mangled_name": "_Z3foov",
            "source_function_id": 7,
        }
    ]

    renamed, datatypes = feature._process_rename_batch(MagicMock(), chunk, MagicMock())

    assert renamed == 1
    assert datatypes == 0
    args = rename.call_args[0]
    assert args[2] == 4096
    assert args[3] == "foo"


def test_process_rename_batch_skips_invalid_address(mocker):
    feature = mf_mod.MatchFunctions(MagicMock())
    mocker.patch.object(mf_mod, "rename_function_util", return_value=True)
    chunk = [
        {
            "function_address": "not-an-int",
            "matched_function_name": "x",
            "matched_mangled_name": "y",
            "source_function_id": 1,
        }
    ]

    renamed, _ = feature._process_rename_batch(MagicMock(), chunk, MagicMock())

    assert renamed == 0
