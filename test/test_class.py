from tin.api import TinApiClass


def test_generic_class_basic():
    api = TinApiClass()

    assert api.obj_path is None
    assert api.classes() == []
    assert api.methods() == []


def test_generic_class_empty_tree():
    api = TinApiClass()
    assert api.tree() == {api: {"classes": {}, "methods": [], "model": None}}


def test_generic_class_empty_json():
    api = TinApiClass()
    assert (
        api.to_json()
        == '{"TinApiClass": {"classes": {}, "methods": [], "model": null}}'
    )


def test_generic_class_repr():
    api = TinApiClass()
    assert "{}".format(api) == "TinApiClass"


def test_generic_class_set_path():
    api = TinApiClass()
    api.obj_path = "/api/path"
    assert api.obj_path == "/api/path"


def test_generic_class_add_method():
    api = TinApiClass()
    fakemethod = object()
    api.add_method("mymethod", fakemethod)
    assert api.methods() == [fakemethod]


def test_generic_class_add_class():
    api = TinApiClass()
    myclass = TinApiClass()
    api.add_class("myclass", myclass)
    assert api.classes() == [myclass]


def test_generic_class_get_class():
    api = TinApiClass()
    myclass = object
    api.add_class("myclass", myclass)
    assert api.get_class("myclass") is myclass


def test_generic_class_tree():
    api = TinApiClass()
    myclass = TinApiClass()
    nextclass = TinApiClass()
    myclass.add_class("NextClass", nextclass)
    mymethod = object()
    nextclass.add_method("nextmethod", mymethod)
    api.add_class("myclass", myclass)
    api.add_method("mymethod", mymethod)

    assert api.tree() == {
        api: {
            "classes": {
                myclass: {
                    "classes": {
                        nextclass: {"classes": {}, "methods": [mymethod], "model": None}
                    },
                    "model": None,
                    "methods": [],
                }
            },
            "methods": [mymethod],
            "model": None,
        }
    }
