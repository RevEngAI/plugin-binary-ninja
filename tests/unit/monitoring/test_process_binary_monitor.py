from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

import revengai

from reai_toolkit.utils.monitoring import process_binary_monitor as pbm_mod


def _bv():
    bv = MagicMock()
    bv.file.filename = "/tmp/sample.elf"
    return bv


def _operation(status, done=False):
    return revengai.OperationCreateMetadataCreateResult(
        done=done,
        name="operations/analyses/2",
        metadata=revengai.CreateMetadata(analysis_id=2, binary_id=1, status=status),
    )


def _operation_without_metadata():
    return revengai.OperationCreateMetadataCreateResult(
        done=False,
        name="operations/analyses/2",
        metadata=None,
    )


def _basic_info(model_id):
    return revengai.AnalysisBasicInfoOutputBody(
        analysis_scope="PRIVATE",
        base_address=4194304,
        binary_id=1,
        binary_name="sample.elf",
        binary_size=1024,
        binary_uuid="0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0",
        creation=datetime(2024, 1, 1, tzinfo=timezone.utc),
        debug=False,
        detected_architecture="x86_64",
        detected_binary_format="ELF",
        detected_binary_type="linux",
        function_count=12,
        is_advanced=False,
        is_owner=True,
        is_system=False,
        model_id=model_id,
        model_name="binnet",
        model_upgrade_available=False,
        owner_username="tester",
        sha_256_hash="0" * 64,
        supplied_architecture="AUTO",
        supplied_binary_format="AUTO",
        supplied_binary_type="AUTO",
        team_id=7,
    )


def test_worker_completes_invokes_callback_and_syncs(mocker):
    captured = {}

    def fake_timer(interval, function, args=()):
        captured["function"] = function
        captured["args"] = args
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.v3_get_analysis_operation.return_value = _operation("Complete", done=True)
    api.get_analysis_basic_info_0.return_value = _basic_info(5)

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    captured["function"](*captured["args"])

    api.v3_get_analysis_operation.assert_called_once_with(2)
    api.get_analysis_basic_info_0.assert_called_once_with(analysis_id=2)
    callback.assert_called_once_with(1, 2, 5)
    checker.sync_service.sync_analysis_data.assert_called_once()


def test_worker_reschedules_while_processing(mocker):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.v3_get_analysis_operation.return_value = _operation("Processing")

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
    api.v3_get_analysis_operation.return_value = _operation(status)

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
    api.v3_get_analysis_operation.return_value = _operation("Error", done=True)

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before
    callback.assert_not_called()
    api.get_analysis_basic_info_0.assert_not_called()
    checker.sync_service.sync_analysis_data.assert_not_called()


def test_worker_treats_unrecognised_status_as_terminal_failure(mocker):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.v3_get_analysis_operation.return_value = _operation("unknown_default_open_api")

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before
    callback.assert_not_called()
    api.get_analysis_basic_info_0.assert_not_called()
    checker.sync_service.sync_analysis_data.assert_not_called()


def test_worker_without_metadata_does_not_complete(mocker):
    timers = []

    def fake_timer(interval, function, args=()):
        timers.append((interval, function, args))
        return MagicMock()

    mocker.patch.object(pbm_mod, "Timer", side_effect=fake_timer)
    api = mocker.patch.object(pbm_mod.revengai, "AnalysesCoreApi").return_value
    api.v3_get_analysis_operation.return_value = _operation_without_metadata()

    checker = pbm_mod.PeriodicChecker(MagicMock())
    checker.sync_service = MagicMock()
    callback = MagicMock()

    checker.start_checking(_bv(), analysis_id=2, binary_id=1, callback=callback)
    before = len(timers)
    timers[-1][1](*timers[-1][2])

    assert len(timers) == before
    callback.assert_not_called()
    api.get_analysis_basic_info_0.assert_not_called()
    checker.sync_service.sync_analysis_data.assert_not_called()
