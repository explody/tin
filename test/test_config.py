import os
import pytest

from tin.config import TinConfig
from tin.exceptions import TinError, TinConfigNotFound


def clear_env():
    for k in os.environ.keys():
        if k.startswith("TIN"):
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


def env_file_config_env_override():
    clear_env()
    os.environ["TIN_CONFIG"] = "test/data/api/testservice.yml"
    os.environ["TIN_ENV"] = "basic"
    os.environ["TIN__ENVIRONMENTS__BASIC__HOST"] = "fakehost"
    os.environ["TIN__ENVIRONMENTS__BASIC__SCHEME"] = "https"
    os.environ["TIN__ENVIRONMENTS__BASIC__PORT"] = "9000"
    ac = TinConfig()

    return ac


def env_full_config():
    clear_env()

    os.environ["TIN__API_NAME"] = "ENV_FULL_API"
    os.environ["TIN__HOST"] = "localhost"
    os.environ["TIN__SCHEME"] = "http"
    os.environ["TIN__PORT"] = "5000"
    os.environ["TIN__BASEPATH"] = "/api"
    os.environ["TIN__AUTH_TYPE"] = "basic"
    os.environ["TIN__SSL__VERIFY"] = "true"
    os.environ["TIN__CONFIG_DIR"] = "test/data/api"
    os.environ["TIN__API_FILE"] = "testservice-api.yml"
    os.environ["TIN__MODEL_FILE"] = "testservice-models.yml"
    os.environ["TIN__CREDENTIALS"] = "credentials.yml"
    ac = TinConfig()

    return ac


def env_prefix_full_config():
    clear_env()

    os.environ["TIN_MYPREFIX__API_NAME"] = "ENV_FULL_API"
    os.environ["TIN_MYPREFIX__HOST"] = "localhost"
    os.environ["TIN_MYPREFIX__SCHEME"] = "http"
    os.environ["TIN_MYPREFIX__PORT"] = "5000"
    os.environ["TIN_MYPREFIX__BASEPATH"] = "/api"
    os.environ["TIN_MYPREFIX__AUTH_TYPE"] = "basic"
    os.environ["TIN_MYPREFIX__SSL__VERIFY"] = "true"
    os.environ["TIN_MYPREFIX__CONFIG_DIR"] = "test/data/api"
    os.environ["TIN_MYPREFIX__API_FILE"] = "testservice-api.yml"
    os.environ["TIN_MYPREFIX__MODEL_FILE"] = "testservice-models.yml"
    os.environ["TIN_MYPREFIX__CREDENTIALS"] = "credentials.yml"
    ac = TinConfig(env_prefix="MYPREFIX")

    return ac


def env_env_config():
    clear_env()

    os.environ["TIN_ENV"] = "basic"
    os.environ["TIN__ENVIRONMENTS__BASIC__HOST"] = "localhost"
    os.environ["TIN__ENVIRONMENTS__BASIC__SCHEME"] = "http"
    os.environ["TIN__ENVIRONMENTS__BASIC__PORT"] = "5000"
    os.environ[
        "TIN__ENVIRONMENTS__BASIC__API_FILE"
    ] = "test/data/api/testservice-api.yml"
    os.environ[
        "TIN__ENVIRONMENTS__BASIC__MODEL_FILE"
    ] = "test/data/api/testservice-models.yml"
    os.environ[
        "TIN__ENVIRONMENTS__BASIC__CREDENTIALS"
    ] = "test/data/api/credentials.yml"
    os.environ["TIN__COMMON__API_NAME"] = "ENV_ENV_API"
    os.environ["TIN__COMMON__AUTH_TYPE"] = "basic"
    os.environ["TIN__COMMON__SSL__VERIFY"] = "true"
    os.environ["TIN__COMMON__BASEPATH"] = "/api"
    ac = TinConfig()

    return ac


def env_prefix_env_config():
    clear_env()

    os.environ["TIN_MYPREFIX_ENV"] = "basic"
    os.environ["TIN_MYPREFIX__ENVIRONMENTS__BASIC__HOST"] = "localhost"
    os.environ["TIN_MYPREFIX__ENVIRONMENTS__BASIC__SCHEME"] = "http"
    os.environ["TIN_MYPREFIX__ENVIRONMENTS__BASIC__PORT"] = "5000"
    os.environ[
        "TIN_MYPREFIX__ENVIRONMENTS__BASIC__API_FILE"
    ] = "test/data/api/testservice-api.yml"
    os.environ[
        "TIN_MYPREFIX__ENVIRONMENTS__BASIC__MODEL_FILE"
    ] = "test/data/api/testservice-models.yml"
    os.environ[
        "TIN_MYPREFIX__ENVIRONMENTS__BASIC__CREDENTIALS"
    ] = "test/data/api/credentials.yml"
    os.environ["TIN_MYPREFIX__COMMON__API_NAME"] = "ENV_ENV_API"
    os.environ["TIN_MYPREFIX__COMMON__AUTH_TYPE"] = "basic"
    os.environ["TIN_MYPREFIX__COMMON__SSL__VERIFY"] = "true"
    os.environ["TIN_MYPREFIX__COMMON__BASEPATH"] = "/api"
    ac = TinConfig(env_prefix="MYPREFIX")

    return ac


def env_json_config_no_environment():
    clear_env()

    os.environ[
        "TIN_CONFIG"
    ] = '{"api_name": "ENV_JSON_API","host":"localhost","scheme":"http","port":5000,"credentials":"test/data/api/credentials.yml","auth_type":"basic","ssl":{"verify":true},"api_file":"test/data/api/testservice-api.yml","model_file":"test/data/api/testservice-models.yml","content-type":"application/json","basepath":"/api","headers":{"someheader":"somevalue"},"default_params":{"thing":"stuff"},"default_tokens":{"otherthing":"morestuff"}}'
    ac = TinConfig()

    return ac


def env_json_config_with_environment():
    clear_env()

    os.environ[
        "TIN_CONFIG"
    ] = '{"environments":{"basic":{"host":"localhost","scheme":"http","port":5000,"credentials":"credentials.yml","auth_type":"basic","ssl":{"verify":true},"api_file":"testservice-api.yml","model_file":"testservice-models.yml"},"param":{"host":"localhost","scheme":"http","port":5000,"credentials":"credentials.yml","auth_type":"param","ssl":{"verify":true},"api_file":"testservice-api.yml","model_file":"testservice-models.yml"}},"common":{"api_name": "ENV_ENV_JSON_API","type":"application/json","config_dir": "test/data/api", "basepath":"/api","headers":{"someheader":"somevalue"},"default_params":{"thing":"stuff"},"default_tokens":{"otherthing":"morestuff"}}}'
    ac = TinConfig(environment="basic")

    return ac


def env_yaml_config_no_environment():
    clear_env()

    os.environ[
        "TIN_CONFIG"
    ] = """---
api_name: ENV_YAML_API
host: localhost
scheme: http
port: 5000
credentials: test/data/api/credentials.yml
auth_type: basic
ssl:
  verify: true
api_file: test/data/api/testservice-api.yml
model_file: test/data/api/testservice-models.yml
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

    os.environ[
        "TIN_CONFIG"
    ] = """---
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
  api_name: ENV_ENV_YAML_API
  type: application/json
  basepath: /api
  config_dir: test/data/api
  headers:
    someheader: somevalue
  default_params:
    thing: stuff
  default_tokens:
    otherthing: morestuff
    """
    ac = TinConfig(environment="basic")

    return ac


def test_error_bad_env_json():
    os.environ["TIN_CONFIG"] = "this will load but yield empty config"
    with pytest.raises(TinError):
        TinConfig()


def test_error_no_api_file():
    with pytest.raises(TinError):
        TinConfig("test/data/api/testservice.yml", "no_api_file")


def test_error_bad_port():
    with pytest.raises(TinError):
        TinConfig("test/data/api/testservice.yml", "bad_port")


def test_error_no_name():
    with pytest.raises(TinError):
        os.environ["TIN__HOST"] = "localhost"
        os.environ["TIN__SCHEME"] = "http"
        os.environ["TIN__PORT"] = "5000"
        os.environ["TIN__BASEPATH"] = "/api"
        os.environ["TIN__AUTH_TYPE"] = "basic"
        os.environ["TIN__SSL__VERIFY"] = "true"
        os.environ["TIN__CONFIG_DIR"] = "test/data/api"
        os.environ["TIN__API_FILE"] = "testservice-api.yml"
        os.environ["TIN__MODEL_FILE"] = "testservice-models.yml"
        os.environ["TIN__CREDENTIALS"] = "credentials.yml"
        ac = TinConfig()


def test_json_in_creds():
    os.environ["TIN__API_NAME"] = "JSON_IN_CREDS"
    os.environ["TIN__HOST"] = "localhost"
    os.environ["TIN__SCHEME"] = "http"
    os.environ["TIN__PORT"] = "5000"
    os.environ["TIN__BASEPATH"] = "/api"
    os.environ["TIN__AUTH_TYPE"] = "basic"
    os.environ["TIN__SSL__VERIFY"] = "true"
    os.environ["TIN__CONFIG_DIR"] = "test/data/api"
    os.environ["TIN__API_FILE"] = "testservice-api.yml"
    os.environ["TIN__MODEL_FILE"] = "testservice-models.yml"
    os.environ["TIN__CREDENTIALS"] = "{'username': 'fake', 'password': 'fake'}"
    ac = TinConfig()
    # assert "maximum recursion" in str(excinfo.value)


def test_arg_config_yml():
    assert type(arg_config_yml()) is TinConfig


def test_config_with_env():
    assert type(env_file_config()) is TinConfig


def test_arg_config_json():
    assert type(arg_config_json()) is TinConfig


def test_no_config():
    with pytest.raises(TinError):
        TinConfig(None, None)


def test_file_but_no_environment():
    with pytest.raises(TinError):
        TinConfig("test/data/api/testservice.yml", None)


def test_file_bad_config():
    with pytest.raises(TinConfigNotFound):
        TinConfig("nosuchfile.yml", "fake")


def test_file_empty_config():
    with pytest.raises(TinError):
        TinConfig("test/data/api/empty.yml", "fake")


def test_file_bad_environment():
    with pytest.raises(TinError):
        TinConfig("test/data/api/testservice.yml", "nosuchenv")


def test_file_no_model_file():
    ac = TinConfig("test/data/api/testservice.yml", "no_models")
    assert ac.models == {}


def test_env_file_with_env_overrides():
    ac = env_file_config_env_override()

    assert ac.host == "fakehost"
    assert ac.scheme == "https"
    assert ac.port == 9000


@pytest.mark.parametrize(
    "config",
    [
        arg_config_yml(),
        arg_config_yml_environment_from_env(),
        arg_config_json(),
        arg_config_json(),
        arg_config_json_environment_from_env(),
        env_file_config(),
    ],
)
class TestFileBasedConfigs:
    def test_config_files(self, config):
        assert config.config_src in [
            os.path.abspath("test/data/api/testservice.yml"),
            os.path.abspath("test/data/api/testservice.json"),
        ]
        assert os.path.join(
            config.config_dir, "testservice-api.yml"
        ) == os.path.abspath("test/data/api/testservice-api.yml")
        assert os.path.join(
            config.config_dir, "testservice-models.yml"
        ) == os.path.abspath("test/data/api/testservice-models.yml")

    def test_config_dir(self, config):
        assert config.config_dir == os.path.dirname(
            os.path.abspath("test/data/api/testservice.yml")
        )

    def test_credentials(self, config):
        print("HERE", config._api_config["auth_type"])
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
        assert config.content_type == "application/json"
        assert config.basepath == "/api"
        assert config.ssl["verify"] is True

    def test_get(self, config):
        assert config.get("host") == "localhost"
        assert config.get("doesntexist") is None


@pytest.mark.parametrize(
    "config",
    [
        env_full_config(),
        env_prefix_full_config(),
        env_env_config(),
        env_prefix_env_config(),
        env_json_config_no_environment(),
        env_json_config_with_environment(),
        env_yaml_config_no_environment(),
        env_yaml_config_with_environment(),
    ],
)
class TestEnvBasedConfigs:
    def test_config_files(self, config):
        assert config.config_src is "ENV"
        if config.config_dir:
            assert (
                os.path.join(config.config_dir, "testservice-api.yml")
                == "test/data/api/testservice-api.yml"
            )
            assert (
                os.path.join(config.config_dir, "testservice-models.yml")
                == "test/data/api/testservice-models.yml"
            )
        else:
            assert config.api_file == "test/data/api/testservice-api.yml"
            assert config.model_file == "test/data/api/testservice-models.yml"

    def test_config_dir(self, config):
        if config.config_dir:
            assert config.config_dir == os.path.dirname("test/data/api/testservice.yml")

    def test_credentials(self, config):
        assert config.credentials == {
            "username": "fakeuser",
            "password": "fakepassword",
        }

    def test_apiname(self, config):
        assert config.api_name in [
            "testservice",
            "ENV_FULL_API",
            "ENV_ENV_API",
            "ENV_JSON_API",
            "ENV_ENV_JSON_API",
            "ENV_YAML_API",
            "ENV_ENV_YAML_API",
        ]

    def test_environment_values(self, config):
        assert config.host == "localhost"
        assert config.scheme == "http"
        assert config.port == 5000
        assert config.auth_type == "basic"
        assert config.content_type == "application/json"
        assert config.basepath == "/api"
        assert config.ssl["verify"] is True

    def test_get(self, config):
        assert config.get("host") == "localhost"
        assert config.get("doesntexist") is None
