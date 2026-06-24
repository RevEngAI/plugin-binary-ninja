from unittest.mock import MagicMock

import pytest

pytest.importorskip("binaryninja")

from reai_toolkit.features.configuration import config as config_mod


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


def test_check_auth_true_when_get_config_succeeds(config, mocker):
    api = mocker.patch.object(config_mod.revengai, "ConfigApi").return_value
    api.get_config.return_value = MagicMock()

    assert config.check_auth() is True
    api.get_config.assert_called_once()


def test_check_auth_false_when_get_config_raises(config, mocker):
    api = mocker.patch.object(config_mod.revengai, "ConfigApi").return_value
    api.get_config.side_effect = Exception("401 unauthorized")

    assert config.check_auth() is False


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
