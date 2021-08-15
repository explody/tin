import simplejson as json


class ApeyeApiModel(dict):
    def __init__(self, data={}):
        if data:
            self.validate(data)
        self._response_data = {}
        self._response = None
        super().__init__(data)

    def validate(self, data):
        for required_attr in self.must:
            if required_attr not in data:
                raise ApeyeModelError(
                    "Required attribute {} not present".format(required_attr)
                )

    def pop(self, key):
        return self[key]

    def popitem(self):
        pass

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
        return json.dumps(self)
