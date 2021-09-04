from apeye.base import ApeyeApiBase
from apeye.exceptions import ApeyeModelError, ApeyeError
from deepmerge import always_merger
import simplejson as json


class ApeyeApiModel(ApeyeApiBase):

    API_METHODS = {"create": None, "read": None, "update": None, "delete": None}

    id_attr = "id"
    _initialized = False

    def __init__(self, data={}):
        ApeyeApiBase.__init__(self)

        self._response_data = {}
        self._response = None
        self._data = data
        if 'id_attr' in data:
            self.id_attr = data['id_attr']

        # These aren't really immutables, just their existence is, for __setattr__
        self._immutables = dir(self)

        self._initialized = True

    def __setattr__(self, key, value):
        if self._initialized:
            if key not in self._immutables:
                self._data[key] = value
                return

        super().__setattr__(key, value)

    def __getattr__(self, item):

        if item in self._data:
            return self._data[item]
        else:
            if item in self.__dict__:
                return self.__dict__[item]
            else:
                self.method_missing(item)

    def method_missing(self, method_name, *args, **kwargs):
        e = "type object '%s' has no attribute '%s'" % (
            self.__class__.__name__,
            method_name,
        )
        raise AttributeError(e)

    def api_method(self, crud_action):
        return self.API_METHODS.get(crud_action, None)

    def validate(self, data):
        for required_attr in self.must:
            if required_attr not in data:
                raise ApeyeModelError(
                    "Required attribute {} not present".format(required_attr)
                )

    def clean(self, data):
        clean_data = dict(data)
        if hasattr(self, 'read'):
            for ro_attr in self.read:
                clean_data.pop(ro_attr)
        return clean_data

    def _confirm_i_have_id(self, action):
        if self.id is None:
            raise ApeyeError(
                "Attempt to call {}() on an instance that isn't "
                "saved yet".format(action)
            )

    def _check_id(self, data):
        if self.id_attr in data:
            if self.id != data[self.id_attr]:
                raise ApeyeError(
                    "Given data has a different ID value ({}) than mine ({}), "
                    "cannot load or merge".format(data[self.id_attr], self.id)
                )

    def create(self, data, **kwargs):

        if not isinstance(data, dict):
            raise ApeyeError("Model data must be a dict")

        self.validate(data)

        # Remove any duplicate/conflicting kwargs.  However, don't ignore all kwargs
        # as there may be other arguments to pass on to the API method
        for k in data.keys():
            if k in kwargs:
                kwargs.pop(k)

        # Remove any 'id' passed in data or kwargs, as new instances mustn't have IDs yet
        if "id" in kwargs:
            kwargs.pop("id")

        if "id" in data:
            data.pop("id")

        self._data = self.API_METHODS["create"](data=data, nomodel=True, **kwargs)

    def refresh(self, **kwargs):
        self._data = self.API_METHODS["read"](id=self.id, nomodel=True, **kwargs)

    def update(self, data, **kwargs):
        # Don't accept an id in kwargs here, is should be in _data
        if "id" in kwargs:
            kwargs.pop("id")

        self._confirm_i_have_id("update")
        self._data = self.API_METHODS["update"](
            id=self.id, data=data, nomodel=True, **kwargs
        )

    def delete(self):
        self._confirm_i_have_id("delete")
        self.API_METHODS["delete"](self.id)
        self._data = None
        return self._data

    def save(self, **kwargs):
        if self.id:
            self.update(self.clean(self._data), **kwargs)
        else:
            self.create(self.clean(self._data), **kwargs)

    def load(self, data):
        self._check_id(data)
        self._data = data

    def merge(self, data):
        self._check_id(data)
        self._data = always_merger.merge(self._data, data)

    @property
    def id(self):
        return self._data.get(self.id_attr, None)

    @property
    def raw(self):
        return self._response_data

    @raw.setter
    def raw(self, response_data):
        self._response_data = response_data

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, response):
        self._response = response

    def to_json(self):
        """Returns self as JSON"""
        return json.dumps(self._data)

    def to_dict(self):
        return self._data
