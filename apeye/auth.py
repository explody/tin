from requests.auth import AuthBase


class HTTPGenericHeaderAuth(AuthBase):
    """Small custom extension of requests auth, for passing auth info in headers"""

    def __init__(self, headers):
        self.headers = headers

    def __call__(self, r):
        r.headers.update(self.headers)
        return r


class HTTPGenericParameterAuth(AuthBase):
    """Small custom extension of requests auth, for passing auth info in query params"""

    def __init__(self, params):
        self.params = params

    def __call__(self, r):
        r.params.update(self.headers)
        return r
