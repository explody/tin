import json
import os
import pytest
import requests

from tin.api import TinApi, TinApiMethod
from tin.exceptions import TinError
from tin.models import TinApiModelFactory
from pytest_httpserver import HTTPServer

model_factory = TinApiModelFactory()
model_type = model_factory("testmodel", {})


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


def test_model_basic():
    data = {"one": 1, "two": "two"}
    model = model_type(data)
    model.newthing = "newval"

    assert model._data == data
    assert model.one == 1
    assert model.two == "two"
    assert "newthing" in model._data
    assert model.to_dict() == {"one": 1, "two": "two", "newthing": "newval"}

    with pytest.raises(AttributeError):
        print(model.doesntexist)

    assert model._response_data == {}
    assert model._response is None


def test_model_load():
    data = {"id": 1, "name": "test"}
    model = model_type(data)
    assert model.name == "test"

    model.load({"id": 1, "name": "new name"})
    assert model.name == "new name"


def test_model_merge():
    data = {"id": 1, "name": "test"}
    model = model_type(data)
    model.merge({"newkey": "new value"})

    assert model.id == 1
    assert model.name == "test"
    assert model.newkey == "new value"


def test_model_loadmerge_bad_id():
    data = {"id": 1, "name": "test"}
    model = model_type(data)

    with pytest.raises(TinError):
        model.load({"id": 2, "name": "test"})

    with pytest.raises(TinError):
        model.merge({"id": 2, "name": "test"})


def test_other_id_attr():
    testservice = api_inst()
    instance = testservice.container.subcontainer2.model(
        {
            "uuid": "639b410e70fe",
            "name": "initial name",
            "description": "initial description",
        }
    )
    assert instance.id == "639b410e70fe"


def test_add_all_methods():
    testservice = api_inst()
    assert testservice.container.subcontainer.model.method_names() == [
        "list",
        "get",
        "create",
        "update",
        "delete",
    ]


def test_add_some_methods():
    testservice = api_inst()
    assert testservice.container.subcontainer2.model.method_names() == ["update"]


def test_exclude_some_methods():
    testservice = api_inst()
    assert testservice.container.subcontainer3.model.method_names() == ["get"]


def test_misconfigured_singleton(httpserver: HTTPServer):
    httpserver.expect_request(
        "/api/stuff/whatnot", json={"send": "this"}, method="POST"
    ).respond_with_json(["one", "two", "three"], status=201)
    testservice = api_inst()

    with pytest.raises(TinError):
        testservice.container.subcontainer.create(data={"send": "this"})


def test_singleton_model(httpserver: HTTPServer):
    httpserver.expect_request("/api/stuff/whatnot/1", method="GET").respond_with_json(
        {"id": 1, "name": "test model", "description": "basic data to build model"}
    )
    testservice = api_inst()
    instance = testservice.container.subcontainer.get(1)
    assert type(instance.response) is requests.Response
    assert type(instance) is testservice.container.subcontainer.model
    assert instance.raw == {
        "id": 1,
        "name": "test model",
        "description": "basic data to build model",
    }

    assert type(instance.api_method("create")) is TinApiMethod
    assert type(instance.api_method("update")) is TinApiMethod


def test_singleton_model_with_key(httpserver: HTTPServer):
    httpserver.expect_request("/api/stuff/whatnot/1", method="GET").respond_with_json(
        {
            "mymodel": {
                "id": 1,
                "name": "test model",
                "description": "basic data to build model",
            }
        }
    )
    testservice = api_inst()
    instance = testservice.container.subcontainer.get(1)
    assert type(instance.response) is requests.Response
    assert type(instance) is testservice.container.subcontainer.model
    assert instance.raw == {
        "mymodel": {
            "id": 1,
            "name": "test model",
            "description": "basic data to build model",
        }
    }

    assert instance.to_dict() == {
        "id": 1,
        "name": "test model",
        "description": "basic data to build model",
    }

    assert type(instance.api_method("create")) is TinApiMethod


def test_model_dict(httpserver: HTTPServer):
    httpserver.expect_request("/api/stuff/whatnot", method="GET").respond_with_json(
        {
            "mymodels": [
                {
                    "id": 1,
                    "name": "test model",
                    "description": "basic data to build model",
                },
                {
                    "id": 1,
                    "name": "test model",
                    "description": "basic data to build model",
                },
            ]
        }
    )
    testservice = api_inst()

    instances = testservice.container.subcontainer.list()
    assert "mymodels" in instances
    assert type(instances.response) is requests.Response

    for instance in instances["mymodels"]:
        assert type(instance) is testservice.container.subcontainer.model
        assert type(instance.raw) is dict
        assert hasattr(instance, "create")
        assert hasattr(instance, "delete")
        assert type(instance.api_method("create")) is TinApiMethod
        assert type(instance.api_method("delete")) is TinApiMethod


def test_model_list(httpserver: HTTPServer):
    httpserver.expect_request("/api/stuff/whatnot", method="GET").respond_with_json(
        [
            {
                "id": 1,
                "name": "test model",
                "description": "basic data to build model",
            },
            {
                "id": 1,
                "name": "test model",
                "description": "basic data to build model",
            },
        ]
    )
    testservice = api_inst()

    instances = testservice.container.subcontainer.list()
    assert len(instances) == 2
    assert type(instances.response) is requests.Response

    for instance in instances:
        assert type(instance) is testservice.container.subcontainer.model
        assert type(instance.raw) is dict
        assert type(instance.api_method("create")) is TinApiMethod
        assert type(instance.api_method("delete")) is TinApiMethod


def test_existing_model_save(httpserver: HTTPServer):
    httpserver.expect_request("/api/stuff/whatnot/1", method="GET").respond_with_json(
        {"id": 1, "name": "test model", "description": "basic data to build model"}
    )

    # Since httpserver needs explicit response data, return something *different*
    # than what is posted, to ensure that when we test the model instance attrs,
    # they're set from data from the _response_, not from what was set on the instance itself
    httpserver.expect_request(
        "/api/stuff/whatnot/1",
        method="PUT",
        json={
            "name": "updated name",
            "description": "updated description",
        },
    ).respond_with_json(
        {"id": 1, "name": "modified name", "description": "modified description"}
    )
    testservice = api_inst()
    instance = testservice.container.subcontainer.get(1)
    instance.description = "updated description"
    instance.name = "updated name"
    instance.save()

    assert instance.description == "modified description"
    assert instance.name == "modified name"

    # Do one with ID and name kwargs to ensure they get stripped
    instance.description = "updated description"
    instance.name = "updated name"
    instance.save(id=10, name="removethis")
    assert instance.id == 1
    assert instance.description == "modified description"
    assert instance.name == "modified name"


def test_new_model_save(httpserver: HTTPServer):
    httpserver.expect_request(
        "/api/stuff/whatnot",
        method="POST",
        json={
            "name": "initial name",
            "description": "initial description",
        },
    ).respond_with_json(
        {"id": 1, "name": "saved name", "description": "saved description"}
    )
    testservice = api_inst()
    instance = testservice.container.subcontainer.model(
        {"name": "initial name", "description": "initial description"}
    )
    instance.save()

    assert instance.id == 1
    assert instance.description == "saved description"
    assert instance.name == "saved name"

    # Do one with ID and name kwargs to ensure they get stripped
    instance = testservice.container.subcontainer.model(
        {"name": "initial name", "description": "initial description"}
    )
    instance.save(id=10, name="removethis")
    assert instance.id == 1
    assert instance.description == "saved description"
    assert instance.name == "saved name"


def test_modify_unsaved():
    testservice = api_inst()
    instance = testservice.container.subcontainer.model(
        {"name": "initial name", "description": "initial description"}
    )
    with pytest.raises(TinError):
        instance.delete()

    with pytest.raises(TinError):
        instance.update({})


def test_model_delete(httpserver: HTTPServer):
    httpserver.expect_request("/api/stuff/whatnot/1", method="GET").respond_with_json(
        {"id": 1, "name": "test model", "description": "basic data to build model"}
    )

    httpserver.expect_request(
        "/api/stuff/whatnot/1",
        method="DELETE",
    ).respond_with_data("", status=204)
    testservice = api_inst()
    instance = testservice.container.subcontainer.get(1)
    assert instance.delete() is None


def test_model_read(httpserver: HTTPServer):
    httpserver.expect_ordered_request(
        "/api/stuff/whatnot/1", method="GET"
    ).respond_with_json(
        {"id": 1, "name": "original name", "description": "original description"}
    )

    # Since httpserver needs explicit response data, return something *different*
    # than what is posted, to ensure that when we test the model instance attrs,
    # they're set from data from the _response_, not from what was set on the instance itself
    httpserver.expect_ordered_request(
        "/api/stuff/whatnot/1",
        method="GET",
    ).respond_with_json(
        {"id": 1, "name": "refreshed name", "description": "refreshed description"}
    )
    testservice = api_inst()
    instance = testservice.container.subcontainer.get(1)

    instance.description = "updated description"
    instance.name = "updated name"
    instance.read()

    assert instance.description == "refreshed description"
    assert instance.name == "refreshed name"
