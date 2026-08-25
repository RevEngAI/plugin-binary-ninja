from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.utils.monitoring import process_binary_monitor as pbm_mod


def _bv():
    bv = MagicMock()
    bv.file.filename = "/tmp/sample.elf"
    return bv


def test_worker_completes_invokes_callback_and_syncs(mocker):
    captured = {}

    def fake_timer(interval, function, args=()):
        captured["function"] = function
        captured["args"] = args
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.get_analysis_status.return_value.data.analysis_status = "Complete"
    api.get_analysis_basic_info.return_value.data.model_id = 5

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    captured["function"](*captured["args"])

    callback.assert_called_once_with(1, 2, 5)
    checker.sync_service.sync_analysis_data.assert_called_once()


def test_worker_reschedules_while_processing(mocker):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.get_analysis_status.return_value.data.analysis_status = "Processing"

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=MagicMock())
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before + 1
    checker.sync_service.sync_analysis_data.assert_not_called()


@pytest.mark.parametrize("status", ["Uploaded", "Queued", "Processing"])
def test_worker_reschedules_for_in_progress_statuses(mocker, status):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.get_analysis_status.return_value.data.analysis_status = status

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=MagicMock())
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before + 1
    checker.sync_service.sync_analysis_data.assert_not_called()


def test_worker_treats_error_status_as_terminal_failure(mocker):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.get_analysis_status.return_value.data.analysis_status = "Error"

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before
    callback.assert_not_called()
    checker.sync_service.sync_analysis_data.assert_not_called()


def test_worker_treats_unrecognised_status_as_terminal_failure(mocker):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.get_analysis_status.return_value.data.analysis_status = "Weird"

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before
    callback.assert_not_called()
    checker.sync_service.sync_analysis_data.assert_not_called()
