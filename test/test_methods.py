import json
import os
import pytest
import requests

from tin.api import TinApi, TinApiMethod
from tin.base import TinApiClass
from tin.exceptions import TinObjectNotFound, TinError, TinInvalidArgs
from tin.models import TinApiModel
from tin.response import (
    TinApiResponseNoContent,
)
from pytest_httpserver import HTTPServer
from types import ModuleType


def clear_env():
    for k in os.environ.keys():
        if k.startswith("TIN"):
            os.environ.pop(k)


def api_inst(env="basic", config="test/data/api/testservice.yml"):
    clear_env()
    # Just a shortcut to keep the repeating text down
    return TinApi(config_file=config, environment=env)


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return ("127.0.0.1", 5000)


@pytest.mark.parametrize(
    "env",
    ["basic", "param", "header", "no_auth", "no_models", "use_session", "no_headers"],
)
def test_available_environments(env):
    testservice = api_inst(env)

    # Objects in the tree are generated so we can't test the specific instances but
    # we know how many there should be, and their type
    stringtree = testservice.tree(True)
    assert len(stringtree) == 1
    assert len(stringtree["testservice"]["classes"]["hasmethods"]["methods"]) == 5
    assert len(stringtree["testservice"]["classes"]["container"]["classes"]) == 4
    assert (
        len(
            stringtree["testservice"]["classes"]["container"]["classes"][
                "subcontainer"
            ]["methods"]
        )
        == 5
    )
    assert (
        len(
            stringtree["testservice"]["classes"]["container"]["classes"][
                "subcontainer2"
            ]["methods"]
        )
        == 5
    )

    def recurse_tree(objtree):
        for k, v in objtree.items():
            if k == "classes":
                # We know the data under 'classes' is a dict, and the keys are objects
                for vkey in v.keys():
                    assert type(vkey) is TinApiClass
            elif k == "methods":
                # We know the value under 'methods' is a list of objects
                for mth in v:
                    assert type(mth) is TinApiMethod
            elif k == "model":
                # We know 'model' is a single model class
                assert type(v) is TinApiModel

    recurse_tree(testservice.tree(False))


@pytest.mark.parametrize(
    "env",
    ["basic", "param", "header", "no_auth", "no_models", "use_session", "no_headers"],
)
def test_named_methods(env):
    testservice = api_inst(env)
    assert type(testservice.hasmethods.update) is TinApiMethod


def test_to_json():
    testservice = api_inst()

    # Arbitrarily chosen method, just to test json output
    from_json = json.loads(testservice.hasmethods.update.to_json())
    for key in ["scheme", "host", "url"]:
        assert key in from_json
        assert type(from_json[key]) is str

    assert type(from_json["port"]) is int
    assert type(from_json["credentials"]) is dict
    assert from_json["credentials"]["username"] == "fakeuser"
    assert from_json["credentials"]["password"] == "fakepassword"

    assert type(from_json["method_data"]) is dict
    assert type(from_json["method_data"]["default_tokens"]) is dict

    for key in ["method", "path", "crud_label"]:
        assert key in from_json["method_data"]
        assert type(from_json["method_data"][key]) is str


def test_path_tokens():
    testservice = api_inst()
    assert testservice.hasmethods.delete.path_tokens() == ["lots", "of", "tokens", "id"]


def test_session():
    testservice = api_inst()
    assert type(testservice.request) is requests.Session


def test_no_session():
    testservice = api_inst("no_session")
    assert isinstance(testservice.request, ModuleType)


def test_missing_token():
    testservice = api_inst()
    with pytest.raises(TinInvalidArgs):
        testservice.hasmethods.delete(1, **{"lots": "one", "of": "two"})


def test_method_list(httpserver: HTTPServer):
    httpserver.expect_request("/api/things", method="GET").respond_with_json(
        ["one", "two", "three"]
    )
    testservice = api_inst()
    assert testservice.hasmethods.list() == ["one", "two", "three"]


def test_subcontainer_method_list(httpserver: HTTPServer):
    httpserver.expect_request("/api/nomodel/items", method="GET").respond_with_json(
        ["one", "two", "three"]
    )
    testservice = api_inst()

    assert testservice.container.nomodel.list() == ["one", "two", "three"]


def test_get(httpserver: HTTPServer):
    httpserver.expect_request("/api/things/1", method="GET").respond_with_json(
        {"single": "item"}
    )
    testservice = api_inst()
    assert testservice.hasmethods.get(1) == {"single": "item"}
    assert testservice.hasmethods.get(id=1) == {"single": "item"}


def test_params(httpserver: HTTPServer):
    httpserver.expect_request("/api/things/1", method="GET").respond_with_json(
        {"single": "item"}
    )
    testservice = api_inst()
    response = testservice.hasmethods.get(id=1, params={"one": 1})
    assert response == {"single": "item"}
    assert (
        response.response.url
        == "http://localhost:5000/api/things/1?thing=stuff&confirm=True&one=1"
    )


def test_post_data(httpserver: HTTPServer):
    httpserver.expect_request(
        "/api/things", json={"send": "this"}, method="POST"
    ).respond_with_json(["one", "two", "three"], status=201)
    testservice = api_inst()
    response = testservice.hasmethods.create(data={"send": "this"})

    # Ensure the requests body matches the data we passed
    assert response.response.request.body == '{"send": "this"}'
    assert response == ["one", "two", "three"]


def test_put_data(httpserver: HTTPServer):
    httpserver.expect_request(
        "/api/things/1", json={"send": "this"}, method="PUT"
    ).respond_with_json(["one", "two", "three"], status=200)
    testservice = api_inst()
    response = testservice.hasmethods.update(id=1, data={"send": "this"})

    # Ensure the requests body matches the data we passed
    assert response.response.request.body == '{"send": "this"}'
    assert response == ["one", "two", "three"]


def test_delete(httpserver: HTTPServer):
    # this test also includes extra path tokens, and the 'nobase' option
    httpserver.expect_request(
        "/things/one/two/three/here/1", method="DELETE"
    ).respond_with_data(None, status=204)
    testservice = api_inst()
    response = testservice.hasmethods.delete(
        1, **{"lots": "one", "of": "two", "tokens": "three"}
    )

    assert type(response) == TinApiResponseNoContent


def test_404(httpserver: HTTPServer):
    httpserver.expect_request("/api/things/1", method="GET").respond_with_data(
        "Not Found", status=404
    )
    testservice = api_inst()
    with pytest.raises(TinObjectNotFound):
        testservice.hasmethods.get(1)


def test_unexpected(httpserver: HTTPServer):
    httpserver.expect_request("/api/things/1", method="GET").respond_with_data(
        "Not Found", status=204
    )
    testservice = api_inst()
    with pytest.raises(TinError):
        testservice.hasmethods.get(1)


def test_bad_json(httpserver: HTTPServer):
    httpserver.expect_request("/api/things/1", method="GET").respond_with_data(
        "this is not JSON", status=200
    )
    testservice = api_inst()
    with pytest.raises(TinError):
        testservice.hasmethods.get(1)


def test_bad_method():
    testservice = api_inst()
    with pytest.raises(TinError):
        testservice.errors.badmethod()


def test_paginate_list(httpserver: HTTPServer):
    httpserver.expect_request("/api/things", method="GET").respond_with_json(
        ["one", "two", "three"],
        headers={"link": ('<http://localhost:5000/api/things/2>; rel="next"')},
    )
    httpserver.expect_request("/api/things/2", method="GET").respond_with_json(
        ["four", "five", "six"]
    )
    testservice = api_inst()
    assert testservice.hasmethods.list() == [
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
    ]

    assert testservice.hasmethods.list(paginate=False) == ["one", "two", "three"]


def test_paginate_dict(httpserver: HTTPServer):
    httpserver.expect_request("/api/things", method="GET").respond_with_json(
        {"results": ["one", "two", "three"]},
        headers={"link": ('<http://localhost:5000/api/things/2>; rel="next"')},
    )
    httpserver.expect_request("/api/things/2", method="GET").respond_with_json(
        {"results": ["four", "five", "six"]}
    )
    testservice = api_inst()

    assert testservice.hasmethods.list() == {
        "results": ["one", "two", "three", "four", "five", "six"]
    }
    assert testservice.hasmethods.list(paginate=False) == {
        "results": ["one", "two", "three"]
    }


def test_paginate_nested_dict(httpserver: HTTPServer):
    httpserver.expect_request("/api/things", method="GET").respond_with_json(
        {"one": ["one"], "two": {"item": "value"}},
        headers={"link": ('<http://localhost:5000/api/things/2>; rel="next"')},
    )
    httpserver.expect_request("/api/things/2", method="GET").respond_with_json(
        {"one": ["two"], "two": {"item": "newvalue"}}
    )
    testservice = api_inst()

    assert testservice.hasmethods.list() == {
        "one": ["one", "two"],
        "two": {"item": "newvalue"},
    }
    assert testservice.hasmethods.list(paginate=False) == {
        "one": ["one"],
        "two": {"item": "value"},
    }
