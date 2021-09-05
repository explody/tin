from tin.exceptions import TinError


class TinApiResponse(object):
    def __init__(self, response_data, response, method):
        self._response = response
        self._response_data = response_data
        self._method = method

    @property
    def response(self):
        return self._response

    @property
    def response_data(self):
        return self._response_data

    @property
    def raw(self):
        return self._response_data


class TinApiResponseDict(TinApiResponse, dict):
    def __init__(self, response_data, response, method, nomodel=False):

        TinApiResponse.__init__(self, response_data, response, method)

        new_data = dict(response_data)

        if (
            hasattr(method.cls, "list_data_key")
            and getattr(method.cls, "list_data_key") in response_data
        ):

            if method.cls.model and not nomodel:
                new_data[method.cls.list_data_key] = []
                object_data = response_data[method.cls.list_data_key]
                for obj in object_data:
                    new_data[method.cls.list_data_key].append(method.cls.model(obj))

        dict.__init__(self, new_data)


class TinApiResponseList(TinApiResponse, list):
    def __init__(self, response_data, response, method, nomodel=False):
        TinApiResponse.__init__(self, response_data, response, method)

        obj_list = []

        if method.cls.model and not nomodel:
            for obj_data in response_data:
                obj_list.append(method.cls.model(obj_data))
        else:
            obj_list = response_data

        list.__init__(self, obj_list)


class TinApiResponseString(TinApiResponse, str):
    def __init__(self, response_data, response, method):
        TinApiResponse.__init__(self, response_data, response, method)
        str.__init__(self, response_data)


class TinApiResponseNoContent(TinApiResponse):
    def __init__(self, response_data, response, method):
        TinApiResponse.__init__(self, response_data, response, method)


class TinApiResponseSingleton(TinApiResponse, dict):
    def __init__(self, response_data, response, method, nomodel=False):
        TinApiResponse.__init__(self, response_data, response, method)
        self.model_instance = None
        if (
            hasattr(method.cls, "singleton_data_key")
            and getattr(method.cls, "singleton_data_key") in response_data
        ):
            singleton_data = response_data[method.cls.singleton_data_key]
        else:
            singleton_data = response_data

        if not isinstance(singleton_data, dict):
            raise TinError(
                "Method {} is configured as singleton but I received a {} from "
                "the API.  Singletons can only be built from dicts".format(
                    method, type(singleton_data)
                )
            )

        if method.cls.model and not nomodel:
            self.model_instance = method.cls.model(singleton_data)
            self.model_instance.raw = response_data
            self.model_instance.response = response
        else:
            dict.__init__(self, singleton_data)

    def instance(self):
        return self.model_instance if self.model_instance else self


class TinApiResponseFactory(object):
    def __call__(self, response_data, response, method, nomodel=False):
        if getattr(method, "expect_return_data", None) == "singleton":
            singleton = TinApiResponseSingleton(
                response_data, response, method, nomodel
            )
            return singleton.instance()
        if isinstance(response_data, list):
            return TinApiResponseList(response_data, response, method, nomodel)
        elif isinstance(response_data, dict):
            return TinApiResponseDict(response_data, response, method, nomodel)
        elif isinstance(response_data, str):
            return TinApiResponseString(response_data, response, method)
        elif response_data is None and response.status_code == 204:
            return TinApiResponseNoContent(response_data, response, method)
