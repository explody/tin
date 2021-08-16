from apeye.api import ApeyeApiClass


def test_generic_class_basic():
    api = ApeyeApiClass()

    assert api.get_objpath() is None
    assert api.classes() == []
    assert api.methods() == []


def test_generic_class_empty_tree():
    api = ApeyeApiClass()
    assert api.tree() == {}


def test_generic_class_empty_json():
    api = ApeyeApiClass()
    assert api.to_json() == '{}'


def test_generic_class_repr():
    api = ApeyeApiClass()
    assert "{}".format(api) == 'ApeyeApiClass'


def test_generic_class_set_path():
    api = ApeyeApiClass()
    api.set_path("/api/path")
    assert api.get_objpath() == "/api/path"


def test_generic_class_add_method():
    api = ApeyeApiClass()
    fakemethod = object()
    api.add_method("mymethod", fakemethod)
    assert api.methods() == [fakemethod]


def test_generic_class_add_class():
    api = ApeyeApiClass()
    myclass = ApeyeApiClass()
    api.add_class("myclass", myclass)
    assert api.classes() == [myclass]


def test_generic_class_get_class():
    api = ApeyeApiClass()
    myclass = object
    api.add_class("myclass", myclass)
    assert api.get_class('myclass') is myclass


def test_generic_class_tree():
    api = ApeyeApiClass()
    myclass = ApeyeApiClass()
    nextclass = ApeyeApiClass()
    myclass.add_class('NextClass', nextclass)
    mymethod = object()
    nextclass.add_method('nextmethod', mymethod)
    api.add_class("myclass", myclass)
    api.add_method("mymethod", mymethod)

    assert api.tree() == {
        'classes': {
            'ApeyeApiClass': {
                'classes': {
                    'ApeyeApiClass': {
                        'methods': [mymethod]
                    }
                }
            }
        },
        'methods': [mymethod]
    }

