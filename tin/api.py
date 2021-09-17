import re
import requests
import simplejson as json
import urllib

from tin.auth import HTTPGenericHeaderAuth, HTTPGenericParameterAuth
from tin.base import TinApiBase, TinApiClass
from tin.config import TinConfig
from tin.exceptions import TinInvalidArgs, TinError, TinObjectNotFound
from tin.models import TinApiModelFactory
from tin.response import TinApiResponseFactory

from deepmerge import always_merger


class TinApi(TinApiClass):
    """The TinApi class represents a complete REST API

    This represents a parent class which contains the object hierarchy which
    will represent the endpoints of the defined REST API.

    Args:
        **kwargs: Arbitrary keyword arguments which will be passed to TinConfig

    Attributes:
        conf (TinConfig): An TinConfig object representing the configuration for
            this API
        tokenre (sre): Compiled regex for locating tokens in the url path string
    """

    def __init__(self, **kwargs):
        super().__init__()

        self.conf = TinConfig(**kwargs)
        self.obj_path = self.conf.api_name

        self._headers = self.conf.headers
        self._auth_obj = self._default_auth()

        self._session = requests.Session() if self.conf.use_session else None

        self.tokenre = re.compile(":([a-zA-Z0-9_-]+)")

        self._model_factory = TinApiModelFactory()
        self._recurse_build_method_path(self, self.conf.apidata, self.obj_path)

    def _recurse_build_method_path(self, obj, api_data, obj_path=None):

        if obj_path is None:
            obj_path = self.conf.api_name

        for cls_name, cls_data in api_data.items():

            new_type = type(cls_name, (TinApiClass,), {})
            container_path = "{}.{}".format(obj_path, cls_name)
            setattr(new_type, "_obj_path", container_path)

            if cls_data.get("model"):

                model_data = self.conf.models.get(cls_data["model"], {})
                model_type = self._model_factory(cls_data["model"], model_data)
                setattr(new_type, "_model", model_type)
                setattr(
                    model_type,
                    "_obj_path",
                    "{}.{}".format(container_path, cls_data["model"]),
                )

            for attr in ["list_data_key", "singleton_data_key"]:
                if cls_data.get(attr):
                    setattr(
                        new_type,
                        attr,
                        cls_data.get(attr),
                    )

            new_obj = new_type()

            obj.add_class(cls_name, new_obj)

            if cls_data.get("methods"):
                # If a child node has 'methods', it's an endpoint

                crud_methods = ["create", "read", "update", "delete"]

                # For each defined method, add an TinApiMethod as
                # an attribute in the current TinApiClass instance
                for mth, mth_data in cls_data["methods"].items():

                    new_method = TinApiMethod(self, new_obj, mth, mth_data)
                    new_method.obj_path = "{}.{}".format(container_path, mth)

                    new_obj.add_method(mth, new_method)

                    # If there is an associated model, it will get ome of the same
                    # methods as the parent class
                    if hasattr(new_type, "_model") and new_type._model is not None:
                        if mth_data.get("model_method_add", None) is False:
                            continue

                        if (
                            mth_data.get("model_method_add", None) is True
                            or cls_data.get("model_methods_add_all", None) is True
                        ):
                            method_name = mth_data.get("model_method_name") or mth
                            new_obj.model.add_method(method_name, new_method)

                            if "crud_label" in mth_data:
                                crud_method = mth_data["crud_label"].lower()
                                if crud_method in crud_methods:
                                    new_obj.model.CRUD_METHODS[
                                        crud_method
                                    ] = new_obj.model.get_method(method_name)

                                    # There can be only one method assigned to each CRUD
                                    # action. As we assign them, remove them from the
                                    # list. If a second/duplicate label shows up in the
                                    # config, it'll just be ignored for not being in
                                    # crud_methods
                                    crud_methods.remove(crud_method)

            else:
                # If there are no methods, it's a container class
                self._recurse_build_method_path(new_obj, cls_data, container_path)

    @property
    def request(self):
        if self._session:
            return self._session
        return requests

    @property
    def headers(self):
        return self._headers

    def set_headers(self, headers, override=False):
        if override:
            self._headers = headers
        else:
            self._headers.update(headers)

    @property
    def auth(self):
        return self._auth_obj

    def set_auth(self, auth_obj):
        self._auth_obj = auth_obj

    def _default_auth(self):
        """Returns a requests auth instance based on the api config"""

        if self.conf.auth_type == "basic":
            return requests.auth.HTTPBasicAuth(
                self.conf.credentials.get("username", None),
                self.conf.credentials.get("password", None),
            )
        elif self.conf.auth_type == "header":
            return HTTPGenericHeaderAuth(self.conf.credentials)
        elif self.conf.auth_type == "param":
            return HTTPGenericParameterAuth(self.conf.credentials)
        else:
            return None


class TinApiMethod(TinApiBase):
    def __init__(self, apiobj, clsobj, name, method_data, obj_path=None):
        """
        The TinApiMethod represents an endpoint method to call on a remote REST API.

        Args:
            apiobj (TinApi): The parent object that contains all classes and methods
                of this API
            clsobj (TinApiClass): The parent object of this method
            name (str): The name of this method
            method_data (dict): A set of information about this method as defined in
                the config YAML

        Attributes:
            name (str): The method name
            api (TinApi): The toplevel APi object
            cls (TinApiClass): The immediate parent TinApiClass object
            method_data (dict): A set of k->v information about the method

        """
        self.name = name
        self.api = apiobj
        self.cls = clsobj
        self._method_data = method_data
        self._response_factory = TinApiResponseFactory()

        self.method = self._method_data["method"]
        self.crud_label = self._method_data.get("crud_label", None)
        self.singleton = self._method_data.get("singleton", False)

        if self._method_data.get("nobase", False):
            self.path = self._method_data["path"]
        else:
            self.path = "{}{}".format(self.api.conf.basepath, self._method_data["path"])

        # If the method specifies an expected return code, grab it, otherwise
        # default to 200
        if "expect" in self._method_data:
            if isinstance(self._method_data["expect"], list):
                self.expect_return_codes = [int(r) for r in self._method_data["expect"]]
            else:
                self.expect_return_codes = [self._method_data["expect"]]
        else:
            self.expect_return_codes = [200]

        if "return" in self._method_data:
            self.expect_return_data = self._method_data["return"]
        else:
            self.expect_return_data = "dict"

        if "paginate" in self._method_data:
            self._paginate = self._method_data["paginate"]
        else:
            self._paginate = True

        self.default_params = (
            self.api.conf.default_params
            if hasattr(self.api.conf, "default_params")
            else {}
        )
        self.default_tokens = (
            self.api.conf.default_tokens
            if hasattr(self.api.conf, "default_tokens")
            else {}
        )

        # If the method has additional default params, merge them in
        if "default_params" in self._method_data:
            self.default_params.update(self._method_data["default_params"])

        # If the method has additional default tokens, merge them in
        if "default_tokens" in self._method_data:
            self.default_tokens.update(self._method_data["default_tokens"])

        self.url = "%s://%s:%s%s" % (
            self.api.conf.scheme,
            self.api.conf.host,
            self.api.conf.port,
            self.path,
        )

        super().__init__()

    def to_json(self):

        return json.dumps(
            {
                "scheme": self.api.conf.scheme,
                "host": self.api.conf.host,
                "port": self.api.conf.port,
                "credentials": self.api.conf.credentials,
                "url": self.url,
                "method_data": self._method_data,
            }
        )

    def path_tokens(self):
        return self.api.tokenre.findall(self.path)

    def __call__(self, id=None, **kwargs):

        # This is where we can put validations on the kwargs,
        # based off data in api.yml (not there yet)

        url = self.url  # FIXME: what?
        data = {}
        params = self.default_params.copy()
        tokens = self.default_tokens.copy()

        # if this is true, TinApiResponseFactory will not instantiate model instances
        # from response data, and just return JSON.  Default is False.
        nomodel = kwargs.pop("nomodel") if "nomodel" in kwargs else False

        # Overwrite with provided arguments. Pop the value out of kwargs.
        if "params" in kwargs:
            params.update(kwargs.pop("params"))

        # No defaults for data.
        if "data" in kwargs:
            data = kwargs.pop("data")
        else:
            data = None

        # Support overriding default paginate behavior with a kwarg
        if "paginate" in kwargs:
            paginate = kwargs.pop("paginate")
        else:
            paginate = self._paginate

        # If 'id' is passed as a positional, it overrides 'id' as a kwarg
        if id is not None:
            kwargs["id"] = id

        # The remaining kwargs *should* correspond to path tokens
        # Merge with defaults, if they exist
        tokens.update(kwargs)

        # Ensure all our path tokens are accounted for
        for tok in self.path_tokens():
            if tok not in tokens:
                raise TinInvalidArgs(
                    "%s called with missing token "
                    "argument %s. For path %s" % (self, tok, self.path)
                )

        # Presence of our path tokens is verified. Replace them in our url
        for k, v in tokens.items():
            url = url.replace(":%s" % k, str(v))

        try:
            response_data = None

            while True:

                # Grab the requests method based on http method name
                try:
                    requests_method = getattr(self.api.request, self.method.lower())
                except AttributeError:
                    raise TinError("Invalid HTTP method: {}".format(self.method))

                # Common arguments with all methods
                request_args = {
                    "headers": self.api.headers,
                    "auth": self.api.auth,
                    "verify": self.api.conf.ssl["verify"],
                    "params": urllib.parse.urlencode(
                        params, quote_via=urllib.parse.quote
                    ),
                }

                # Add data if we have any
                if data:
                    request_args["data"] = json.dumps(data)

                # Call the requests method
                response = requests_method(url, **request_args)

                if response.status_code == 404:
                    raise TinObjectNotFound(
                        "Object not found. Tried: {}. "
                        "Remote API says: {}".format(url, response.text)
                    )
                elif response.status_code not in self.expect_return_codes:
                    raise TinError(
                        "ERROR at {} Got return code {}, expected {}. "
                        "Remote API says: {}".format(
                            url,
                            response.status_code,
                            ",".join([str(r) for r in self.expect_return_codes]),
                            response.text,
                        )
                    )

                if response.status_code == 204:
                    response_data = None
                    break
                else:
                    try:
                        current_response_data = response.json()
                    except Exception:
                        # FIXME: excessively generic exception
                        raise TinError(
                            "ERROR decoding response JSON. "
                            "Raw response is: {}".format(response.content)
                        )

                    # If we're paginating, this recursively merges the current response
                    # with preceding ones
                    if response_data:
                        response_data = always_merger.merge(
                            response_data, current_response_data
                        )
                    else:
                        response_data = current_response_data

                    if "next" not in response.links or not paginate:
                        break
                    else:
                        url = response.links["next"]["url"]

                # This next bit appears to have been almost exclusively for Oomnitza and
                # their weird header-based paginating.  I'll leave it here for reference
                # if we find enough APIs that do something like this but otherwise I
                # think this would be better in the code using Tin.

                # # Handle pagination types
                # # "header_count" expects a total passed over in the HTTP header
                # if (hasattr(self.api.conf, "pagination")) and (
                #     self.api.conf.pagination["type"] == "header_count"
                # ):
                #     header_count = response.headers.get(
                #         self.api.conf.pagination["header"], "0"
                #     )  # if the specified header doesn't exist, assume 0 addt'l pages
                #
                #     response_count["current"] = len(current_response_data)
                #     response_count["total"] = len(response_data)
                #
                #     # If we haven't fetched all the records, set the config'd
                #     # path or params then continue
                #     if response_count["total"] < int(header_count):
                #
                #         v = self.api.conf.pagination["value"]
                #
                #         if "param" in self.api.conf.pagination:
                #             p = self.api.conf.pagination["param"]
                #             params[p] = response_count[v]
                #         elif "path" in self.api.conf.pagination:
                #             n = self.api.conf.pagination["path"]
                #             path = n % response_count[v]
                #             url = "%s/%s" % (url, path)
                #     else:
                #         break

        except requests.exceptions.HTTPError as e:
            raise TinError("ERROR: %s" % e)

        return self._response_factory(response_data, response, self, nomodel)
