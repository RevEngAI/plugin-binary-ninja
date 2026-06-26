from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.upload import upload_dialog as dialog_mod


def _fake_dialog(tier_result):
    """A stand-in for UploadDialog exposing only what _apply_tier_restrictions touches.

    Real QWidget construction aborts under Binary Ninja headless CI, so we drive
    the method with a mock self instead of instantiating the dialog.
    """
    dlg = MagicMock()
    dlg.uploader.get_user_tier.return_value = tier_result
    return dlg


def test_enthusiast_disables_private():
    dlg = _fake_dialog((True, dialog_mod.ENTHUSIAST_TIER))

    dialog_mod.UploadDialog._apply_tier_restrictions(dlg)

    dlg.private_radio.setChecked.assert_called_once_with(False)
    dlg.private_radio.setEnabled.assert_called_once_with(False)
    dlg.private_radio.setToolTip.assert_called_once_with(dialog_mod.PRIVATE_DISABLED_TOOLTIP)
    dlg.public_radio.setChecked.assert_called_once_with(True)


def test_non_enthusiast_keeps_private_enabled():
    dlg = _fake_dialog((True, "REVERSER"))

    dialog_mod.UploadDialog._apply_tier_restrictions(dlg)

    dlg.private_radio.setEnabled.assert_not_called()
    dlg.private_radio.setToolTip.assert_not_called()
    dlg.public_radio.setChecked.assert_not_called()


def test_tier_lookup_failure_leaves_private_enabled():
    dlg = _fake_dialog((False, None))

    dialog_mod.UploadDialog._apply_tier_restrictions(dlg)

    dlg.private_radio.setEnabled.assert_not_called()
    dlg.private_radio.setToolTip.assert_not_called()
    dlg.public_radio.setChecked.assert_not_called()
