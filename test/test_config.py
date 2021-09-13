import os
import pytest

from tin.config import TinConfig
from tin.exceptions import TinError, TinConfigNotFound


def clear_env():
    for k in os.environ.keys():
        if k.startswith('TIN'):
            os.environ.pop(k)


def arg_config_yml():
    clear_env()
    return TinConfig("test/data/api/testservice.yml", "basic")


def arg_config_yml_environment_from_env():
    clear_env()
    os.environ["TIN_ENV"] = "basic"
    return TinConfig("test/data/api/testservice.yml")


def arg_config_json():
    clear_env()
    return TinConfig("test/data/api/testservice.json", "basic")


def arg_config_json_environment_from_env():
    clear_env()
    os.environ["TIN_ENV"] = "basic"
    return TinConfig("test/data/api/testservice.json")


def env_file_config():
    clear_env()
    os.environ["TIN_CONFIG"] = "test/data/api/testservice.yml"
    os.environ["TIN_ENV"] = "basic"
    ac = TinConfig()

    return ac


def env_full_config():
    clear_env()

    os.environ["TIN__HOST"] = "localhost"
    os.environ["TIN__SCHEME"] = "http"
    os.environ["TIN__PORT"] = "5000"
    os.environ["TIN__AUTHTYPE"] = "basic"
    os.environ["TIN__SSL__VERIFY"] = "true"
    ac = TinConfig()

    return ac

def env_env_config():
    clear_env()

    os.environ["TIN__BASIC__HOST"] = "localhost"
    os.environ["TIN__BASIC__SCHEME"] = "http"
    os.environ["TIN__BASIC__PORT"] = "5000"
    os.environ["TIN__COMMON_AUTHTYPE"] = "basic"
    os.environ["TIN__COMMON_SSL__VERIFY"] = "true"
    ac = TinConfig()

    return ac


def env_json_config_no_environment():
    clear_env()

    os.environ["TIN_CONFIG"] = '{"host":"localhost","scheme":"http","port":5000,"credentials":"credentials.yml","auth_type":"basic","ssl":{"verify":true},"api_file":"testservice-api.yml","model_file":"testservice-models.yml","content-type":"application/json","basepath":"/api","headers":{"someheader":"somevalue"},"default_params":{"thing":"stuff"},"default_tokens":{"otherthing":"morestuff"}}'
    ac = TinConfig()

    return ac


def env_json_config_with_environment():
    clear_env()

    os.environ["TIN_CONFIG"] = '{"environments":{"basic":{"host":"localhost","scheme":"http","port":5000,"credentials":"credentials.yml","auth_type":"basic","ssl":{"verify":true},"api_file":"testservice-api.yml","model_file":"testservice-models.yml"},"param":{"host":"localhost","scheme":"http","port":5000,"credentials":"credentials.yml","auth_type":"param","ssl":{"verify":true},"api_file":"testservice-api.yml","model_file":"testservice-models.yml"}},"common":{"type":"application/json","basepath":"/api","headers":{"someheader":"somevalue"},"default_params":{"thing":"stuff"},"default_tokens":{"otherthing":"morestuff"}}}'
    ac = TinConfig(environment='basic')

    return ac

def env_yaml_config_no_environment():
    clear_env()

    os.environ["TIN_CONFIG"] = """---
host: localhost
scheme: http
port: 5000
credentials: credentials.yml
auth_type: basic
ssl:
  verify: true
api_file: testservice-api.yml
model_file: testservice-models.yml
content-type: application/json
basepath: /api
headers:
  someheader: somevalue
default_params:
  thing: stuff
default_tokens:
  otherthing: morestuff
    """
    ac = TinConfig()

    return ac


def env_yaml_config_with_environment():
    clear_env()

    os.environ["TIN_CONFIG"] = """---
environments:
  basic:
    host: localhost
    scheme: http
    port: 5000
    credentials: credentials.yml
    auth_type: basic
    ssl:
      verify: true
    api_file: testservice-api.yml
    model_file: testservice-models.yml
  param:
    host: localhost
    scheme: http
    port: 5000
    credentials: credentials.yml
    auth_type: param
    ssl:
      verify: true
    api_file: testservice-api.yml
    model_file: testservice-models.yml
common:
  type: application/json
  basepath: /api
  headers:
    someheader: somevalue
  default_params:
    thing: stuff
  default_tokens:
    otherthing: morestuff
    """
    ac = TinConfig(environment='basic')

    return ac


def test_arg_config_yml():
    assert type(arg_config_yml()) is TinConfig


def test_config_with_env():
    assert type(env_file_config()) is TinConfig


def test_arg_config_json():
    assert type(arg_config_json()) is TinConfig


def test_no_config():
    with pytest.raises(TinError):
        TinConfig(None, None)


def test_no_environment():
    with pytest.raises(TinError):
        TinConfig("test/data/api/testservice.yml", None)


def test_bad_config():
    with pytest.raises(TinConfigNotFound):
        TinConfig("nosuchfile.yml", "fake")


def test_empty_config():
    with pytest.raises(TinError):
        TinConfig("test/data/api/empty.yml", "fake")


def test_bad_environment():
    with pytest.raises(TinError):
        TinConfig("test/data/api/testservice.yml", "nosuchenv")


def test_no_models():
    ac = TinConfig("test/data/api/testservice.yml", "no_models")
    assert ac.models == {}


@pytest.mark.parametrize("config", [arg_config_yml(), env_file_config(), arg_config_json()])
class TestConfig:
    def test_config_files(self, config):

        assert config.config_file in [
            os.path.abspath("test/data/api/testservice.yml"),
            os.path.abspath("test/data/api/testservice.json"),
        ]
        assert config.api_file == os.path.abspath("test/data/api/testservice-api.yml")
        assert config.model_file == os.path.abspath(
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
        assert config.host == "localhost"
        assert config.scheme == "http"
        assert config.port == 5000
        assert config.auth_type == "basic"
        assert config.type == "application/json"
        assert config.basepath == "/api"
        assert config.ssl["verify"] is True

    def test_get(self, config):
        assert config.get("host") == "localhost"
        assert config.get("doesntexist") is None

    # def test_environments(self, config):
    #     assert config.environments == ['basic', 'param', 'header']
