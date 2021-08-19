import os
import pytest

from apeye.config import ApeyeConfig
from apeye.exceptions import ApeyeError, ApeyeConfigNotFound


def arg_config_yml():
    return ApeyeConfig("test/data/api/testservice.yml", "basic")


def arg_config_json():
    return ApeyeConfig("test/data/api/testservice.json", "basic")


def env_config():
    os.environ["APEYE_CONFIG"] = "test/data/api/testservice.yml"
    os.environ["APEYE_ENV"] = "basic"
    ac = ApeyeConfig()
    os.environ.pop("APEYE_CONFIG")
    os.environ.pop("APEYE_ENV")
    return ac


def test_arg_config_yml():
    assert type(arg_config_yml()) is ApeyeConfig


def test_config_with_env():
    assert type(env_config()) is ApeyeConfig


def test_arg_config_json():
    assert type(arg_config_json()) is ApeyeConfig


def test_no_config():
    with pytest.raises(ApeyeError):
        ApeyeConfig(None, None)


def test_no_environment():
    with pytest.raises(ApeyeError):
        ApeyeConfig("test/data/api/testservice.yml", None)


def test_bad_config():
    with pytest.raises(ApeyeConfigNotFound):
        ApeyeConfig("nosuchfile.yml", "fake")


def test_empty_config():
    with pytest.raises(ApeyeError):
        ApeyeConfig("test/data/api/empty.yml", "fake")


def test_bad_environment():
    with pytest.raises(ApeyeError):
        ApeyeConfig("test/data/api/testservice.yml", "nosuchenv")


def test_no_models():
    ac = ApeyeConfig("test/data/api/testservice.yml", "no_models")
    assert ac.models == {}


@pytest.mark.parametrize("config", [arg_config_yml(), env_config(), arg_config_json()])
class TestConfig:
    def test_config_files(self, config):

        assert config.config_file in [
            os.path.abspath("test/data/api/testservice.yml"),
            os.path.abspath("test/data/api/testservice.json"),
        ]
        assert config.apifile == os.path.abspath("test/data/api/testservice-api.yml")
        assert config.modelfile == os.path.abspath(
            "test/data/api/testservice-models.yml"
        )

    def test_config_dir(self, config):
        assert config.config_dir == os.path.dirname(
            os.path.abspath("test/data/api/testservice.yml")
        )

    def test_credentials(self, config):
        assert config.credentials == {
            "username": "fakeuser",
            "password": "fakepassword",
        }

    def test_apiname(self, config):
        assert config.api_name == "testservice"

    def test_environment_values(self, config):
        print(config.config_file)
        assert config.host == "localhost"
        assert config.scheme == "http"
        assert config.port == 5000
        assert config.authtype == "basic"
        assert config.type == "application/json"
        assert config.basepath == "/api"
        assert config.ssl["verify"] is True

    def test_get(self, config):
        assert config.get("host") == "localhost"
        assert config.get("doesntexist") is None

    # def test_environments(self, config):
    #     assert config.environments == ['basic', 'param', 'header']
