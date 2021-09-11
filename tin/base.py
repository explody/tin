import json


class TinApiBase(object):

    _obj_path = None

    def __init__(self):
        pass

    def __repr__(self):
        """Represents self as a string"""
        return self._obj_path if self._obj_path else type(self).__name__

    def basename(self):
        return self._obj_path.split(".")[-1] if self._obj_path else type(self).__name__

    @property
    def obj_path(self):
        return self._obj_path

    @obj_path.setter
    def obj_path(self, obj_path):
        self._obj_path = obj_path


class TinApiClass(TinApiBase):
    """Simple class for holding additional TinApiClass's and TinApiMethod's"""

    _model = None

    def __init__(self, obj_path=None):
        self._methods = []
        self._classes = {}
        if obj_path:
            self.obj_path = obj_path
        super().__init__()

    def add_method(self, name, method):
        setattr(self, name, method)
        self._methods.append(name)

    def add_class(self, name, cls):
        setattr(self, name, cls)
        self._classes[name] = cls

    def methods(self):
        return [getattr(self, mth) for mth in self._methods]

    def classes(self):
        return [cls for cls in self._classes.values()]

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, model):
        self._model = model

    def get_class(self, name):
        return self._classes[name]

    def _recurse(self, obj, toplevel=True, strings=False):
        """Recurses through defined classes and methods and
        builds a dict of their names"""
        layer = {"classes": {}, "methods": [], "model": None}

        for mth in obj.methods():
            layer["methods"].append(mth.basename() if strings else mth)
        for cls in obj.classes():
            layer["classes"][cls.basename() if strings else cls] = self._recurse(
                cls, False, strings
            )

        if obj.model:
            layer["model"] = obj.model.__name__ if strings else obj.model

        if toplevel:
            layer = {str(self) if strings else self: layer}

        return layer

    def tree(self, strings=False):
        """Returns an informational dict of the object/method hierarchy,
        as name strings"""
        return self._recurse(self, True, strings)

    def to_json(self):
        """Returns the tree as JSON"""
        return json.dumps(self._recurse(self, True, True))
