from threading import Timer
from typing import Optional
from binaryninja import log_info, log_error
import revengai
from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import QTimer, QObject, Signal

_STATUS_UNINITIALISED = "UNINITIALISED"
_STATUS_COMPLETED = "COMPLETED"
_STATUS_FAILED = "FAILED"

_PHASE_DECOMP = "decomp"
_PHASE_SUMMARY = "summary"
_PHASE_COMMENTS = "comments"
_PHASE_DONE = "done"


def _normalise_status(status) -> str:
    return str(status).strip().upper()


def _format_summary_as_comment(summary: str) -> str:
    body = "\n".join(f" * {line}" for line in summary.strip().splitlines())
    return f"/*\n{body}\n */"


def _inject_inline_comments(code: str, comments) -> str:
    lines = code.split("\n")
    for c in sorted(comments, key=lambda x: x.line, reverse=True):
        idx = c.line - 1
        if idx < 0 or idx >= len(lines):
            continue
        target = lines[idx]
        indent = target[: len(target) - len(target.lstrip())]
        lines.insert(idx, f"{indent}// {c.comment}")
    return "\n".join(lines)


class AIDecompilerChecker(QObject):
    update_text_signal = Signal(object, str)

    def __init__(self):
        super().__init__()
        self._current_timer: Optional[Timer] = None
        self._ai_decompiler_timer: Optional[QTimer] = None
        self.number_of_clicks = 0
        self.flag = False
        self._function_id: Optional[int] = None
        self._phase = _PHASE_DECOMP
        self._decompilation: Optional[str] = None
        self._summary_text: Optional[str] = None
        self._inline_comments = None
        self._summary_requeued = False
        self._comments_requeued = False
        self.update_text_signal.connect(self._update_text_slot)

    def _update_text_slot(self, callback, text):
        try:
            if hasattr(callback, '__call__'):
                if hasattr(self, '_current_editor'):
                    callback(self._current_editor, text)
        except Exception as ex:
            log_error(f"RevEng.AI | Error updating UI: {str(ex)}")

    def stop(self):
        if self._current_timer:
            self._current_timer.cancel()
            self._current_timer = None
            log_info("RevEng.AI | Stopped periodic status check")

        if self._ai_decompiler_timer:
            self._ai_decompiler_timer.stop()
            self._ai_decompiler_timer = None
            log_info("RevEng.AI | Stopped AI decompiler periodic check")

    def start_ai_decompiler_checking(self, function_id: int, callback, editor: QPlainTextEdit, name: str, config) -> None:
        try:
            log_info(f"RevEng.AI | Starting AI decompiler periodic check for: {name}")
            self._current_editor = editor
            self._current_callback = callback
            self._current_config = config

            self._function_id = function_id
            self._phase = _PHASE_DECOMP
            self._decompilation = None
            self._summary_text = None
            self._inline_comments = None
            self._summary_requeued = False
            self._comments_requeued = False

            if self._ai_decompiler_timer:
                self._ai_decompiler_timer.stop()

            self._ai_decompiler_timer = QTimer()
            self._ai_decompiler_timer.timeout.connect(self._ai_decompiler_worker)
            self._ai_decompiler_timer.start(1000)

            log_info(f"RevEng.AI | Started AI decompiler periodic check for: {name}")

            self._ai_decompiler_worker()

        except Exception as ex:
            log_error(f"RevEng.AI | Error starting AI decompiler check: {str(ex)}")

    def _api(self, api_client):
        return revengai.FunctionsAIDecompilationApi(api_client)

    def _render(self):
        parts = []
        if self._summary_text:
            parts.append(_format_summary_as_comment(self._summary_text))

        body = self._decompilation or ""
        if self._inline_comments:
            body = _inject_inline_comments(body, self._inline_comments)

        text = "\n".join(parts + [body]) if parts else body
        self.update_text_signal.emit(self._current_callback, text)

    def _run_decomp_phase(self):
        fid = self._function_id
        with self._current_config.create_api_client() as api_client:
            status = _normalise_status(self._api(api_client).get_ai_decompilation_status(fid).status)
        log_info(f"RevEng.AI | AI Decompilation status for Function ID {fid}: {status}")

        if status == _STATUS_UNINITIALISED:
            with self._current_config.create_api_client() as api_client:
                response = self._api(api_client).create_ai_decompilation(fid)
            if not getattr(response, "status", False):
                raise Exception(f"AI Decompilation for Function ID {fid} failed to start")
            log_info(f"RevEng.AI | AI Decompilation task created for Function ID {fid}")
            return

        if status == _STATUS_FAILED:
            raise Exception(f"AI Decompilation for Function ID {fid} failed")

        if status != _STATUS_COMPLETED:
            return

        with self._current_config.create_api_client() as api_client:
            self._decompilation = self._api(api_client).get_ai_decompilation(fid).decompilation
        log_info(f"RevEng.AI | AI Decompilation for Function ID {fid} completed")
        self._render()
        self._phase = _PHASE_SUMMARY

    def _run_summary_phase(self):
        fid = self._function_id
        try:
            with self._current_config.create_api_client() as api_client:
                summary = self._api(api_client).get_ai_decompilation_summary(fid)
            status = _normalise_status(summary.task_status)

            if status == _STATUS_COMPLETED:
                self._summary_text = summary.ai_summary
                self._render()
                self._phase = _PHASE_COMMENTS
                return

            if status == _STATUS_FAILED:
                log_error(f"RevEng.AI | AI summary generation failed for Function ID {fid}")
                self._phase = _PHASE_COMMENTS
                return

            if status == _STATUS_UNINITIALISED and not self._summary_requeued:
                self._requeue(self._api_regenerate_summary, fid, "summary")
                self._summary_requeued = True

        except Exception as ex:
            log_error(f"RevEng.AI | Error fetching AI summary for Function ID {fid}: {str(ex)}")
            self._phase = _PHASE_COMMENTS

    def _run_comments_phase(self):
        fid = self._function_id
        try:
            with self._current_config.create_api_client() as api_client:
                comments = self._api(api_client).get_ai_decompilation_inline_comments(fid)
            status = _normalise_status(comments.task_status)

            if status == _STATUS_COMPLETED:
                self._inline_comments = comments.inline_comments
                self._render()
                self._finish()
                return

            if status == _STATUS_FAILED:
                log_error(f"RevEng.AI | Inline comment generation failed for Function ID {fid}")
                self._finish()
                return

            if status == _STATUS_UNINITIALISED and not self._comments_requeued:
                self._requeue(self._api_regenerate_comments, fid, "inline comments")
                self._comments_requeued = True

        except Exception as ex:
            log_error(f"RevEng.AI | Error fetching inline comments for Function ID {fid}: {str(ex)}")
            self._finish()

    def _api_regenerate_summary(self, api_client, fid):
        self._api(api_client).regenerate_ai_decompilation_summary(fid)

    def _api_regenerate_comments(self, api_client, fid):
        self._api(api_client).regenerate_ai_decompilation_inline_comments(fid)

    def _requeue(self, regenerate_fn, fid, label):
        try:
            with self._current_config.create_api_client() as api_client:
                regenerate_fn(api_client, fid)
            log_info(f"RevEng.AI | Requested {label} generation for Function ID {fid}")
        except Exception as ex:
            log_info(f"RevEng.AI | Could not (re)queue {label} for Function ID {fid}: {str(ex)}")

    def _finish(self):
        self._phase = _PHASE_DONE
        self.update_text_signal.emit(lambda x, y: self.stop(), "")

    def _ai_decompiler_worker(self):
        if self.flag:
            log_info("RevEng.AI | AI Decompilation tick already in progress")
            return
        self.flag = True
        try:
            if self._phase == _PHASE_DECOMP:
                self._run_decomp_phase()
            elif self._phase == _PHASE_SUMMARY:
                self._run_summary_phase()
            elif self._phase == _PHASE_COMMENTS:
                self._run_comments_phase()
        except Exception as ex:
            log_error(f"RevEng.AI | Error in AI decompiler worker: {str(ex)}")
            self.update_text_signal.emit(self._current_callback, f"AI Decompilation failed: {ex}")
            self._finish()
        finally:
            self.flag = False
