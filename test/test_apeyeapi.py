from apeye.api import ApeyeApi
from apeye.auth import HTTPGenericHeaderAuth, HTTPGenericParameterAuth
import pytest
import requests


@pytest.mark.parametrize(
    "env",
    ["basic", "param", "header", "no_auth", "no_models", "use_session", "no_headers"],
)
def test_available_environments(env):
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment=env)
    assert type(myapi) is ApeyeApi


def test_use_session_by_default():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="basic")
    assert type(myapi.request) is requests.Session


def test_use_session_explicit():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="use_session")
    assert type(myapi.request) is requests.Session


def test_no_session():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="no_session")
    assert myapi.request is requests


def test_common_headers():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="basic")
    assert myapi.headers == {"someheader": "somevalue"}


def test_no_headers():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="no_headers")
    assert myapi.headers == {}


def test_set_headers():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="basic")
    myapi.set_headers({"thing": "stuff"})
    assert myapi.headers == {"someheader": "somevalue", "thing": "stuff"}

    myapi.set_headers({"someheader": "othervalue"})
    assert myapi.headers == {"someheader": "othervalue", "thing": "stuff"}

    myapi.set_headers({"otherheader": "differentvalue"}, True)
    assert myapi.headers == {"otherheader": "differentvalue"}


def test_basic_auth():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="basic")
    assert type(myapi.auth) is requests.auth.HTTPBasicAuth


def test_header_auth():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="header")
    assert type(myapi.auth) is HTTPGenericHeaderAuth


def test_param_auth():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="param")
    assert type(myapi.auth) is HTTPGenericParameterAuth

def test_set_auth():
    myapi = ApeyeApi(config_file="test/data/api/testservice.yml", environment="no_auth")
    fakeauth = object()
    myapi.set_auth(fakeauth)
    assert myapi.auth is fakeauth