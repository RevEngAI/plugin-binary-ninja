from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

import inspect
import re

import revengai

from reai_toolkit.features.configuration import config as config_mod


def _auth_settings_for(api_cls, serializer):
    source = inspect.getsource(getattr(api_cls, serializer))
    block = re.search(r"_auth_settings: List\[str\] = \[(.*?)\]", source, re.S)
    return re.findall(r"'([^']+)'", block.group(1)) if block else []


class FakeSettings:
    def __init__(self):
        self.store = {}

    def register_group(self, *args, **kwargs):
        return True

    def register_setting(self, *args, **kwargs):
        return True

    def get_string(self, key, default=None):
        return self.store.get(key, default if default is not None else "")

    def set_string(self, key, value):
        self.store[key] = value
        return True

    def get_json(self, key, default=None):
        return self.store.get(key, "null")

    def set_json(self, key, value):
        self.store[key] = value
        return True


@pytest.fixture
def settings():
    return FakeSettings()


@pytest.fixture
def config(mocker, settings):
    mocker.patch.object(config_mod, "Settings", return_value=settings)
    return config_mod.Config()


def test_api_key_is_sent_unprefixed(config):
    """The SDK applies an operation's auth settings in order onto the same
    Authorization header, so configuring access_token alongside api_key turns
    every request into "Bearer <key>". The gateway rejects that on /v3/upload
    with a 403, so the api-key scheme must stay the only one configured."""
    config.host = "https://example.invalid"
    config.api_key = "secret-key"
    config.init_api_config()

    assert set(config.api_config.auth_settings()) == {"APIKey"}

    headers = {}
    with config.create_api_client() as client:
        client.update_params_for_auth(
            headers, [], ["APIKey", "bearerAuth"], "/v3/upload", "POST", None
        )

    assert headers["Authorization"] == "secret-key"


def test_get_me_declares_bearer_auth_only(config):
    """GET /v2/iam/me is the one operation this plugin calls that declares
    bearerAuth alone, so it gets no Authorization header and the tier lookup
    401s. get_user_tier treats that as non-fatal. Tracked separately: the fix
    has to scope bearer credentials to this call, not the whole client."""
    assert _auth_settings_for(revengai.IAMUsersApi, "_get_me_serialize") == ["bearerAuth"]


def test_check_auth_true_when_get_config_succeeds(config, mocker):
    api = mocker.patch.object(config_mod.revengai, "ConfigApi").return_value
    api.v3_get_config.return_value = MagicMock()

    assert config.check_auth() is True
    api.v3_get_config.assert_called_once()


def test_check_auth_false_when_get_config_raises(config, mocker):
    api = mocker.patch.object(config_mod.revengai, "ConfigApi").return_value
    api.v3_get_config.side_effect = Exception("401 unauthorized")

    assert config.check_auth() is False


def test_init_config_uses_v3_binary_search(config, mocker):
    mocker.patch.object(config_mod, "get_sha256", return_value="deadbeef")
    mocker.patch.object(config, "check_auth", return_value=True)
    sync = mocker.patch.object(config_mod, "AnalysisSyncService")
    api = mocker.patch.object(config_mod.revengai, "BinariesApi").return_value
    api.v3_search_binaries.return_value = MagicMock(
        results=[MagicMock(binary_id=11, analysis_id=22, model_id=33)]
    )
    config.api_key = "key"

    ok, _ = config.init_config(MagicMock())

    assert ok is True
    api.v3_search_binaries.assert_called_once_with(
        partial_sha256="deadbeef", user_files_only=True
    )
    assert (config.binary_id, config.analysis_id, config.model_id) == (11, 22, 33)
    sync.return_value.sync_analysis_data.assert_called_once()


def test_init_config_raises_when_v3_search_returns_no_results(config, mocker):
    mocker.patch.object(config_mod, "get_sha256", return_value="deadbeef")
    mocker.patch.object(config, "check_auth", return_value=True)
    api = mocker.patch.object(config_mod.revengai, "BinariesApi").return_value
    api.v3_search_binaries.return_value = MagicMock(results=[])
    config.api_key = "key"

    ok, message = config.init_config(MagicMock())

    assert ok is False
    assert "not found" in message


def test_set_current_info_round_trips_through_settings(config):
    config.sha256 = "abc123"

    config.set_current_info(11, 22, 33)

    assert config.get_all_analyses()["abc123"] == {
        "binary_id": 11,
        "analysis_id": 22,
        "model_id": 33,
    }


def test_get_binary_id_returns_zero_when_unknown(config, mocker):
    mocker.patch.object(config_mod, "get_sha256", return_value="deadbeef")

    assert config.get_binary_id(MagicMock()) == 0


def test_get_analysis_id_returns_stored_value(config, mocker):
    mocker.patch.object(config_mod, "get_sha256", return_value="deadbeef")
    config.sha256 = "deadbeef"
    config.set_current_info(1, 2, 3)

    assert config.get_analysis_id(MagicMock()) == 2


def test_reset_analysis_data_removes_entry(config, mocker):
    mocker.patch.object(config_mod, "get_sha256", return_value="deadbeef")
    config.sha256 = "deadbeef"
    config.set_current_info(1, 2, 3)

    ok, _ = config.reset_analysis_data(MagicMock())

    assert ok is True
    assert "deadbeef" not in config.get_all_analyses()
