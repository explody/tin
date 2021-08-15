class ApeyeApiResponse(object):
    def __init__(self, response_data, response):
        self._response = response
        self._response_data = response_data

    @property
    def response(self):
        return self._response

    @property
    def response_data(self):
        return self._response_data

    @property
    def raw(self):
        return self._response_data


class ApeyeApiResponseDict(ApeyeApiResponse, dict):
    def __init__(self, response_data, response, method):

        ApeyeApiResponse.__init__(self, response_data, response)

        new_data = dict(response_data)

        if (
            hasattr(method.cls, "response_list_path")
            and getattr(method.cls, "response_list_path") in response_data
        ):

            new_data[method.cls.response_list_path] = []
            object_data = response_data[method.cls.response_list_path]
            for obj in object_data:
                new_data[method.cls.response_list_path].append(method.cls.model(obj))

        dict.__init__(self, new_data)


class ApeyeApiResponseList(list, ApeyeApiResponse):
    def __init__(self, response_data, response, method):
        ApeyeApiResponse.__init__(self, response_data, response)

        obj_list = []

        for obj_data in response_data:
            obj_list.append(method.cls.model(obj_data))

        list.__init__(self, obj_list)


class ApeyeApiResponseString(str, ApeyeApiResponse):
    def __init__(self, response_data, response, api):
        super().__init__(response_data, response, api)


class ApeyeApiResponseFactory(object):
    def __call__(self, response_data, response, method):
        if getattr(method, "singleton", False):
            if (
                hasattr(method.cls, "response_single_path")
                and getattr(method.cls, "response_single_path") in response_data
            ):
                model_instance = method.cls.model(
                    response_data[method.cls.response_single_path]
                )
            else:
                model_instance = method.cls.model(response_data)

            model_instance.raw = response_data
            model_instance.response = response
            return model_instance

        if isinstance(response_data, list):
            return ApeyeApiResponseList(response_data, response, method)
        elif isinstance(response_data, dict):
            return ApeyeApiResponseDict(response_data, response, method)
        else:
            return ApeyeApiResponseString(response_data, response, method)
