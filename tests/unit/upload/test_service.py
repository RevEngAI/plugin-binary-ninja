import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

pytest.importorskip("binaryninja")

from reai_toolkit.features.upload import upload as upload_mod


@pytest.fixture
def uploader():
    return upload_mod.BinaryUploader(MagicMock())


def test_get_models_returns_models(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "ConfigApi").return_value
    api.v3_get_models.return_value.models = ["binnet-0.5", "binnet-0.4"]

    ok, models = uploader.get_models(MagicMock())

    assert ok is True
    assert models == ["binnet-0.5", "binnet-0.4"]


def test_get_models_handles_missing_models(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "ConfigApi").return_value
    api.v3_get_models.return_value.models = None

    ok, models = uploader.get_models(MagicMock())

    assert ok is True
    assert models == []


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


def test_get_user_tier_falls_back_when_the_user_model_fails_validation(uploader, mocker):
    """The SDK marks User fields required that /v2/iam/me does not always send.
    A strict parse then raises and the tier is lost, so the raw body is re-read.
    """
    api = mocker.patch.object(upload_mod.revengai, "IAMUsersApi").return_value
    api.get_me.side_effect = ValidationError.from_exception_data("User", [])
    api.get_me_without_preload_content.return_value = SimpleNamespace(
        status=200,
        data=json.dumps({"tier": upload_mod.ENTHUSIAST_TIER}),
    )

    ok, tier = uploader.get_user_tier()

    assert ok is True
    assert tier == upload_mod.ENTHUSIAST_TIER


def test_get_user_tier_surfaces_a_non_200_from_the_fallback(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "IAMUsersApi").return_value
    api.get_me.side_effect = ValidationError.from_exception_data("User", [])
    api.get_me_without_preload_content.return_value = SimpleNamespace(status=500, data="")

    ok, tier = uploader.get_user_tier()

    assert ok is False
    assert tier is None


def test_get_user_tier_surfaces_failure(uploader, mocker):
    api = mocker.patch.object(upload_mod.revengai, "IAMUsersApi").return_value
    api.get_me.side_effect = Exception("boom")

    ok, tier = uploader.get_user_tier()

    assert ok is False
    assert tier is None


def test_upload_binary_returns_a_tuple_when_the_upload_fails(mocker):
    """upload_binary's caller unpacks two values. Returning a bare False on the
    failure paths raised "cannot unpack non-iterable bool object" and masked the
    real upload error."""
    uploader = upload_mod.BinaryUploader(MagicMock())
    mocker.patch.object(uploader, "upload_file", return_value=(False, "403 Forbidden"))
    bv = MagicMock()
    bv.file.filename = "/tmp/sample.bin"
    bv.parent_view.length = 1024
    mocker.patch.object(upload_mod.Path, "read_bytes", return_value=b"\x00")

    ok, message = uploader.upload_binary(bv, {"debug_info": None, "tags": [], "is_private": True})

    assert ok is False
    assert message == "403 Forbidden"


def test_upload_binary_returns_a_tuple_when_the_file_is_too_large(mocker):
    uploader = upload_mod.BinaryUploader(MagicMock())
    bv = MagicMock()
    bv.file.filename = "/tmp/big.bin"
    bv.parent_view.length = 11 * 1024 ** 2
    mocker.patch.object(upload_mod.Path, "read_bytes", return_value=b"\x00")

    ok, message = uploader.upload_binary(bv, {"debug_info": None, "tags": [], "is_private": True})

    assert ok is False
    assert "too large" in message


def test_upload_binary_includes_every_function_boundary(mocker):
    """The platform reads a boundary with no include_in_analysis flag as excluded
    and fails the analysis, so every boundary must say it is included."""
    uploader = upload_mod.BinaryUploader(MagicMock())
    mocker.patch.object(uploader, "upload_file", return_value=(True, "abc123"))
    mocker.patch.object(upload_mod, "PeriodicChecker")
    analyses_api = mocker.patch.object(upload_mod.revengai, "AnalysesCoreApi")
    bv = MagicMock()
    bv.file.filename = "/tmp/sample.bin"
    bv.parent_view.length = 1024
    bv.image_base = 0x400000
    func = MagicMock(start=0x401000, total_bytes=0x20)
    func.name = "main"
    bv.functions = [func]
    mocker.patch.object(upload_mod.Path, "read_bytes", return_value=b"\x00")

    uploader.upload_binary(bv, {"debug_info": None, "tags": [], "is_private": True})

    request = analyses_api.return_value.create_analysis.call_args.kwargs["analysis_create_request"]
    boundaries = request.symbols.function_boundaries
    assert len(boundaries) == 1
    assert boundaries[0].include_in_analysis is True
