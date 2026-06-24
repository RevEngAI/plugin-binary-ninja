from collections import namedtuple
from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.utils.monitoring import ai_decompiler_monitor as mon_mod


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    from PySide6.QtCore import QCoreApplication

    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


@pytest.fixture
def api(mocker):
    return mocker.patch.object(
        mon_mod.revengai, "FunctionsAIDecompilationApi"
    ).return_value


@pytest.fixture
def checker():
    instance = mon_mod.AIDecompilerChecker()
    instance._current_config = MagicMock()
    instance._current_callback = MagicMock()
    instance._current_editor = object()
    instance._function_id = 42
    instance._phase = mon_mod._PHASE_DECOMP
    instance._summary_requeued = False
    instance._comments_requeued = False
    instance._decompilation = None
    instance._summary_text = None
    instance._inline_comments = None
    return instance


def _status(value):
    return MagicMock(status=value)


def test_decomp_uninitialised_triggers_create(checker, api):
    api.get_ai_decompilation_status.return_value = _status("UNINITIALISED")
    api.create_ai_decompilation.return_value = MagicMock(status=True)

    checker._ai_decompiler_worker()

    api.create_ai_decompilation.assert_called_once_with(42)
    assert checker._phase == mon_mod._PHASE_DECOMP


def test_decomp_completed_advances_to_summary(checker, api):
    api.get_ai_decompilation_status.return_value = _status("COMPLETED")
    api.get_ai_decompilation.return_value = MagicMock(decompilation="int main() {}")

    checker._ai_decompiler_worker()

    assert checker._decompilation == "int main() {}"
    assert checker._phase == mon_mod._PHASE_SUMMARY
    checker._current_callback.assert_called()


def test_decomp_failed_finishes(checker, api):
    api.get_ai_decompilation_status.return_value = _status("FAILED")

    checker._ai_decompiler_worker()

    assert checker._phase == mon_mod._PHASE_DONE


def test_summary_completed_advances_to_comments(checker, api):
    checker._phase = mon_mod._PHASE_SUMMARY
    api.get_ai_decompilation_summary.return_value = MagicMock(
        task_status="COMPLETED", ai_summary="does X"
    )

    checker._ai_decompiler_worker()

    assert checker._summary_text == "does X"
    assert checker._phase == mon_mod._PHASE_COMMENTS


def test_summary_uninitialised_requeues_once(checker, api):
    checker._phase = mon_mod._PHASE_SUMMARY
    api.get_ai_decompilation_summary.return_value = MagicMock(task_status="UNINITIALISED")

    checker._ai_decompiler_worker()
    checker._ai_decompiler_worker()

    api.regenerate_ai_decompilation_summary.assert_called_once_with(42)
    assert checker._summary_requeued is True


def test_comments_completed_finishes(checker, api):
    checker._phase = mon_mod._PHASE_COMMENTS
    api.get_ai_decompilation_inline_comments.return_value = MagicMock(
        task_status="COMPLETED", inline_comments=[]
    )

    checker._ai_decompiler_worker()

    assert checker._phase == mon_mod._PHASE_DONE


def test_render_injects_summary_and_inline_comments(checker):
    Comment = namedtuple("Comment", "line comment")
    checker._summary_text = "summary line"
    checker._decompilation = "int main() {\n    return 0;\n}"
    checker._inline_comments = [Comment(2, "returns zero")]

    checker._render()

    text = checker._current_callback.call_args[0][1]
    assert "/*" in text
    assert "summary line" in text
    assert "// returns zero" in text
