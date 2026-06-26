from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.upload import upload as upload_mod


@pytest.fixture
def uploader():
    return upload_mod.BinaryUploader(MagicMock())


def test_get_models_returns_models(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "ModelsApi").return_value
    api.get_models.return_value.data.models = ["binnet-0.5", "binnet-0.4"]

    ok, models = uploader.get_models(MagicMock())

    assert ok is True
    assert models == ["binnet-0.5", "binnet-0.4"]


def test_upload_file_returns_sha_and_forwards_args(uploader, mocker, tmp_path):
    api = mocker.patch.object(upload_mod.revengai, "AnalysesCoreApi").return_value
    api.upload_file.return_value.data.sha_256_hash = "deadbeef"
    binary = tmp_path / "bin.elf"
    binary.write_bytes(b"\x7fELF\x02\x01")

    ok, sha = uploader.upload_file(str(binary), upload_mod.revengai.UploadFileType.BINARY)

    assert ok is True
    assert sha == "deadbeef"
    args, kwargs = api.upload_file.call_args
    assert args[0] == upload_mod.revengai.UploadFileType.BINARY
    assert args[1] == b"\x7fELF\x02\x01"
    assert kwargs["force_overwrite"] is True


def test_upload_file_surfaces_error(uploader, mocker, tmp_path):
    api = mocker.patch.object(upload_mod.revengai, "AnalysesCoreApi").return_value
    api.upload_file.side_effect = Exception("boom")
    binary = tmp_path / "bin.elf"
    binary.write_bytes(b"\x7fELF")

    ok, message = uploader.upload_file(str(binary), upload_mod.revengai.UploadFileType.BINARY)

    assert ok is False
    assert "boom" in message


def test_get_user_tier_returns_tier(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "IAMUsersApi").return_value
    api.get_me.return_value.tier = upload_mod.ENTHUSIAST_TIER

    ok, tier = uploader.get_user_tier()

    assert ok is True
    assert tier == upload_mod.ENTHUSIAST_TIER
    api.get_me.assert_called_once_with()


def test_get_user_tier_surfaces_failure(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "IAMUsersApi").return_value
    api.get_me.side_effect = Exception("boom")

    ok, tier = uploader.get_user_tier()

    assert ok is False
    assert tier is None
