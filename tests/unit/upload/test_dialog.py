from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.upload import upload_dialog as dialog_mod


@pytest.fixture(scope="module", autouse=True)
def _qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _make_dialog(tier_result):
    uploader = MagicMock()
    uploader.get_user_tier.return_value = tier_result
    dialog = dialog_mod.UploadDialog(MagicMock(), uploader, MagicMock())
    return dialog


def test_enthusiast_disables_private():
    dialog = _make_dialog((True, dialog_mod.ENTHUSIAST_TIER))
    try:
        assert dialog.private_radio.isEnabled() is False
        assert dialog.private_radio.isChecked() is False
        assert dialog.public_radio.isChecked() is True
        assert dialog.private_radio.toolTip() == dialog_mod.PRIVATE_DISABLED_TOOLTIP
        assert dialog.get_upload_options()["is_private"] is False
    finally:
        dialog.close()


def test_non_enthusiast_keeps_private_enabled():
    dialog = _make_dialog((True, "REVERSER"))
    try:
        assert dialog.private_radio.isEnabled() is True
        assert dialog.private_radio.isChecked() is True
        assert dialog.private_radio.toolTip() == ""
        assert dialog.get_upload_options()["is_private"] is True
    finally:
        dialog.close()


def test_tier_lookup_failure_leaves_private_enabled():
    dialog = _make_dialog((False, None))
    try:
        assert dialog.private_radio.isEnabled() is True
        assert dialog.private_radio.isChecked() is True
        assert dialog.get_upload_options()["is_private"] is True
    finally:
        dialog.close()
