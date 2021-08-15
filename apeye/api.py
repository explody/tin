import re
import requests
import urllib
import simplejson as json

from apeye.auth import HTTPGenericHeaderAuth, HTTPGenericParameterAuth
from apeye.config import ApeyeConfig
from apeye.exceptions import ApeyeInvalidArgs
from apeye.models import ApeyeApiModel
from apeye.response import ApeyeApiResponseFactory


class ApeyeApiClass(object):
    """Simple class for holding additional ApeyeApiClass's and ApeyeApiMethod's"""

    def __init__(self, objpath=None):
        self._methods = []
        self._classes = {}
        self._objpath = objpath

    def __repr__(self):
        """Represents self as a string"""
        return type(self).__name__

    def get_objpath(self):
        return self._objpath

    def set_path(self, objpath):
        self._objpath = objpath

    def add_method(self, name):
        self._methods.append(name)

    def add_class(self, name, cls):
        self._classes[name] = cls

    def methods(self):
        return [getattr(self, mth) for mth in self._methods]

    def classes(self):
        return [cls for cls in self._classes.values()]

    def get_class(self, name):
        return self._classes[name]

    def _recurse(self, obj, strings=False):
        """Recurses through defined classes and methods and builds a dict of their names"""
        layer = {"classes": {}, "methods": []}
        for mth in obj.methods():
            layer["methods"].append(str(mth) if strings else mth)
        for cls in obj.classes():
            layer["classes"][str(cls)] = self._recurse(cls, strings)

        if not layer["classes"]:
            del layer["classes"]

        if not layer["methods"]:
            del layer["methods"]

        return layer

    def tree(self):
        """Returns an informational dict of the object/method hierarchy, as name strings"""
        return self._recurse(self)

    def to_json(self):
        """Returns the tree as JSON"""

        return json.dumps(self._recurse(self, True))


class ApeyeApi(ApeyeApiClass):
    """The ApeyeApi class represents a complete REST API

    This represents a parent class which contains the object hierarchy which
    will represent the endpoints of the defined REST API.

    Args:
        **kwargs: Arbitrary keyword arguments which will be passed to ApeyeConfig

    Attributes:
        conf (ApeyeConfig): An ApeyeConfig object representing the configuration for this API
        tokenre (sre): Compiled regex for locating tokens in the url path string
    """

    def __init__(self, **kwargs):
        super(ApeyeApi, self).__init__()

        self.conf = ApeyeConfig(**kwargs)

        self._headers = self.conf.headers
        self._auth_obj = self._default_auth()

        self._session = requests.Session() if self.conf.use_session else None

        if self.conf.apidata.get("swagger", False):

            self.tokenre = re.compile("{([a-zA-Z0-9_-]+)}")

            for path, pdata in self.conf.apidata["paths"].items():

                # If there is a base path specified, remove it from the path string we're working on
                mpath = (
                    re.sub("^%s" % self.conf.basepath, "", path)
                    if self.conf.basepath
                    else path
                )

                # Remove leading and trailing slashes so we split cleanly
                mpath = mpath.strip("/")
                mparts = mpath.split("/")

                for hmth, hmthdata in pdata.items():
                    # The mangling here is specifically for django-rest-swagger,
                    # to try and build a sane method path
                    if hmthdata["operationId"]:

                        mthname = hmthdata["operationId"]

                        # based on the way that django-rest-swagger generates operationId's
                        # trim them from left to right to remove the redundant path strings
                        mthpath = []
                        for part in mparts:
                            if self.tokenre.match(part):
                                continue
                            mthpath.append(part)
                            mthname = re.sub("^%s_" % part, "", mthname)

                        mthdata = self._swagger_method_data(
                            "/%s" % mpath, hmth, hmthdata
                        )

                        self._recurse_build_method_path_swagger(
                            self, mthpath, mthname, mthdata
                        )
                    else:
                        print(
                            "Swagger definitions with operationId's are not currently supported"
                        )
                        sys.exit()

        else:
            self.tokenre = re.compile(":([a-zA-Z0-9_-]+)")
            self._recurse_build_method_path(self, self.conf.apidata)

    def _recurse_build_method_path(self, obj, api_data):

        for cls, cls_data in api_data.items():

            new_type = type(cls, (ApeyeApiClass,), {})

            if cls_data.get("model"):
                model_data = self.conf.models.get(cls_data["model"], {})
                model_type = type(cls_data["model"], (ApeyeApiModel,), model_data)
                setattr(new_type, "model", model_type)

            for attr in ["response_list_path", "response_single_path"]:
                if cls_data.get(attr):
                    setattr(
                        new_type,
                        attr,
                        cls_data.get(attr),
                    )

            new_obj = new_type()

            if cls_data.get("methods"):
                # If a child node has 'methods', it's an endpoint

                # For each defined method, add an ApeyeApiMethod as
                # an attribute in the current ApeyeApiClass instance
                for mth, mth_data in cls_data["methods"].items():
                    new_method = ApeyeApiMethod(self, new_obj, mth, mth_data)
                    setattr(new_obj, mth, new_method)

                    # If there is an associated model, it will get the same methods
                    # as the parent class
                    if hasattr(new_type, "model"):
                        # Only add methods to the object model that are explicitly labeled as
                        # object methods
                        if "object_method" in mth_data:
                            setattr(new_type.model, mth, new_method)

                    new_obj.add_method(mth)

            else:
                # If there are no methods, it's a container class
                self._recurse_build_method_path(new_obj, cls_data)

            setattr(obj, cls, new_obj)
            obj.add_class(cls, getattr(obj, cls))

    def _swagger_method_data(self, path, mth, mthdata):
        """Constructs a dictionary of data about an ApeyeApiMethod, from swagger data"""

        return {
            "method": mth.upper(),
            "path": path,
            "return": list(mthdata["responses"].keys()),
        }

    def _recurse_build_method_path_swagger(
        self, obj, paths, mth, mthdata, objpath=None
    ):
        """Builds a hierarchy of objects representing the paths to the REST endpoints

        The ApeyeApiClass instances are effectively containers. Given an array that represents
        the components of an endpoint path. e.g. /path/to/endpoint == ['path', 'to', 'endpoint']
        and an initial container object, this would produce a hierarchy of objects/attributes with
        a method at the end.

        path.to.endpoint (ApeyeApiClass.ApeyeApiClass.ApeyeApiMethod)

        With the intention of the final endpoint will contain one or more ApeyeApiMethod attributes

        Args:
            obj (ApeyeApiClass): The object in which to add the next attribute
            paths (list): A list of strings that represent the path/object hierarchy
            mth (str): The name of the method
            mthdata (dict): A set of data about the method
            objpath (str): The full object path as a string. e.g. "path.to.endpoint"
        """
        current = paths[0].replace("-", "_")

        # If no objpath is given, we're at the firs element of the paths list
        if objpath is None:
            objpath = current

        # As this is intended to be run multiple times with multiple path lists, see if the current
        # object already has the first element created and if so, use that. Otherwise create a
        # new type object which inherits from ApeyeApiClass
        if hasattr(obj, current):
            this_obj = getattr(obj, current)
        else:
            new_type = type(current, (ApeyeApiClass,), {})
            this_obj = new_type(objpath)
            setattr(obj, current, this_obj)
            obj.add_class(current, getattr(obj, current))

        # If there are remaining path items, recurse, passing the child object (this_obj)
        # as the starting point, and constructing the objpath as we go.
        if len(paths[1:]) > 0:
            self._recurse_build_method_path_swagger(
                this_obj, paths[1:], mth, mthdata, ".".join(paths[0:2])
            )
        else:
            # If there are no further path elements, create the method on this_obj
            setattr(this_obj, mth, ApeyeApiMethod(self, this_obj, mth, mthdata))
            this_obj.add_method(mth)

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

        if self.conf.authtype == "basic":
            u = self.conf.credentials.get("username", None)
            p = self.conf.credentials.get("password", None)
            return requests.auth.HTTPBasicAuth(u, p)
        elif self.conf.authtype == "header":
            return HTTPGenericHeaderAuth(self.conf.credentials)
        elif self.conf.authtype == "param":
            return HTTPGenericParameterAuth(self.conf.credentials)
        else:
            return None


class ApeyeApiMethod(object):
    def __init__(self, apiobj, clsobj, name, method_data):
        """
        The ApeyeApiMethod represents an endpoint method to call on a remote REST API.

        Args:
            apiobj (ApeyeApi): The parent object that contains all classes and methods of this API
            clsobj (ApeyeApiClass): The parent object of this method
            name (str): The name of this method
            method_data (dict): A set of information about this method as defined in the config YAML
                or Swagger JSON

        Attributes:
            name (str): The method name
            api (ApeyeApi): The toplevel APi object
            cls (ApeyeApiClass): The immediate parent ApeyeApiClass object
            method_data (dict): A set of k->v information about the method

        """
        self.name = name
        self.api = apiobj
        self.cls = clsobj
        self._md = method_data

        self.method = self._md["method"]
        self.object_method = self._md.get("object_method", None)
        self.singleton = self._md.get("singleton", False)

        if self._md.get("nobase", False):
            self.path = self._md["path"]
        else:
            self.path = "{}{}".format(self.api.conf.basepath, self._md["path"])

        # If the method specifies an expected return code, grab it, otherwise
        # default to 200
        if "return" in self._md:
            if isinstance(self._md["return"], list):
                self.expect_return = [int(r) for r in self._md["return"]]
            elif isinstance(self._md["return"], dict):
                self.expect_return = [int(r) for r in self._md["return"].keys()]
            else:
                self.expect_return = [self._md["return"]]
        else:
            self.expect_return = [200]

        self.default_params = {}
        self.default_tokens = {}

        # Start with default parameters for the api and method, if they exist
        if hasattr(self.api.conf, "default_params"):
            self.default_params.update(self.api.conf.default_params)

        if "default_params" in self._md:
            self.default_params.update(self._md["default_params"])
            self.may += self._md["default_params"]

        # Start with default path tokens for the api and method, if they exist
        if hasattr(self.api.conf, "default_tokens"):
            self.default_tokens.update(self.api.conf.default_tokens)

        if "default_tokens" in self._md:
            self.default_tokens.update(self._md["default_tokens"])

        self.url = "%s://%s:%s%s" % (
            self.api.conf.scheme,
            self.api.conf.host,
            self.api.conf.port,
            self.path,
        )

    def to_json(self):

        return json.dumps(
            {
                "scheme": self.scheme,
                "host": self.host,
                "port": self.port,
                "credentials": self.creds,
                "url": self.url,
                "method_data": self._md,
            }
        )

    def path_tokens(self):
        return self.api.tokenre.findall(self.path)

    def __repr__(self):

        if self.cls.get_objpath():
            return "%s" % (self.name)
        else:
            return "%s.%s.%s" % (self.api.conf.api_name, self.cls, self.name)

    def __call__(self, id=None, **kwargs):

        # This is where we can put validations on the kwargs,
        # based off data in api.yml (not there yet)

        url = self.url
        data = {}
        params = self.default_params.copy()
        tokens = self.default_tokens.copy()

        # Overwrite with provided arguments. Pop the value out of kwargs.
        if "params" in kwargs:
            params.update(kwargs.pop("params"))

        # No defaults for data.
        if "data" in kwargs:
            data = kwargs.pop("data")
        else:
            data = None

        # If 'id' is passed as a positional, it overrides 'id' as a kwarg
        if id is not None:
            kwargs["id"] = id

        # The remaining kwargs *should* correspond to path tokens
        # Merge with defaults, if they exist
        tokens.update(kwargs)

        # Ensure all our path tokens are accounted for
        for tok in self.path_tokens():
            if tok not in tokens:
                raise ApeyeInvalidArgs(
                    "%s called with missing token "
                    "argument %s. For path %s" % (self, tok, self.path)
                )

        # Presence of our path tokens is verified. Replace them in our url
        for k, v in tokens.items():
            if self.api.conf.apidata.get("swagger", False):
                url = url.replace("{%s}" % k, str(v))
            else:
                url = url.replace(":%s" % k, str(v))

        try:
            response_data = None
            response_count = {}
            while True:
                if self.method == "GET":
                    response = self.api.request.get(
                        url,
                        headers=self.api.headers,
                        auth=self.api.auth,
                        verify=self.api.conf.ssl["verify"],
                        params=urllib.parse.urlencode(
                            params, quote_via=urllib.parse.quote
                        ),
                    )
                elif self.method == "OPTIONS":
                    response = self.api.request.options(
                        url,
                        headers=self.api.headers,
                        auth=self.api.auth,
                        verify=self.api.conf.ssl["verify"],
                        params=urllib.parse.urlencode(
                            params, quote_via=urllib.parse.quote
                        ),
                    )
                elif self.method == "POST":
                    response = self.api.request.post(
                        url,
                        data=json.dumps(data),
                        headers=self.api.headers,
                        auth=self.api.auth,
                        verify=self.api.conf.ssl["verify"],
                        params=urllib.parse.urlencode(
                            params, quote_via=urllib.parse.quote
                        ),
                    )
                elif self.method == "PATCH":
                    response = self.api.request.patch(
                        url,
                        data=json.dumps(data),
                        headers=self.api.headers,
                        auth=self.api.auth,
                        verify=self.api.conf.ssl["verify"],
                        params=urllib.parse.urlencode(
                            params, quote_via=urllib.parse.quote
                        ),
                    )
                elif self.method == "PUT":
                    response = self.api.request.put(
                        url,
                        data=json.dumps(data),
                        headers=self.api.headers,
                        auth=self.api.auth,
                        verify=self.api.conf.ssl["verify"],
                        params=urllib.parse.urlencode(
                            params, quote_via=urllib.parse.quote
                        ),
                    )
                elif self.method == "DELETE":
                    response = self.api.request.delete(
                        url,
                        data=json.dumps(data),
                        headers=self.api.headers,
                        auth=self.api.auth,
                        verify=self.api.conf.ssl["verify"],
                        params=urllib.parse.urlencode(
                            params, quote_via=urllib.parse.quote
                        ),
                    )

                if response.status_code == 404:
                    raise ApeyeObjectNotFound(
                        "Object not found. Tried: %s. "
                        "Apeye says: %s" % (url, response.text)
                    )
                elif response.status_code not in self.expect_return:
                    raise ApeyeError(
                        "ERROR at %s Got return code %s, expected %s. Apeye says: %s"
                        % (
                            url,
                            response.status_code,
                            ",".join([str(r) for r in self.expect_return]),
                            response.text,
                        )
                    )

                try:
                    current_response_data = response.json()
                except Exception as e:
                    raise ApeyeError(
                        "ERROR decoding response JSON. "
                        "Raw response is: %s" % response.text
                    )

                if isinstance(response_data, list):
                    response_data.extend(current_response_data)
                elif isinstance(response_data, dict):
                    response_data.update(current_response_data)
                else:
                    response_data = current_response_data

                # Handle pagination types
                # "header_count" expects a total passed over in the HTTP header
                #
                if (hasattr(self.api.conf, "pagination")) and (
                    self.api.conf.pagination["type"] == "header_count"
                ):
                    header_count = response.headers.get(
                        self.api.conf.pagination["header"], "0"
                    )  # if the specified header doesn't exist, assume 0 addt'l pages

                    response_count["current"] = len(current_response_data)
                    response_count["total"] = len(response_data)

                    # If we haven't fetched all the records, set the config'd
                    # path or params then continue
                    if response_count["total"] < int(header_count):

                        v = self.api.conf.pagination["value"]

                        if "param" in self.api.conf.pagination:
                            p = self.api.conf.pagination["param"]
                            params[p] = response_count[v]
                        elif "path" in self.api.conf.pagination:
                            n = self.api.conf.pagination["path"]
                            path = n % response_count[v]
                            url = "%s/%s" % (url, path)
                    else:
                        break

                else:
                    if "next" not in response.links:
                        break
                    else:
                        url = response.links["next"]["url"]

        except requests.exceptions.HTTPError as e:
            raise ApeyeError("ERROR: %s" % e)

        response_factory = ApeyeApiResponseFactory()
        return response_factory(response_data, response, self)
