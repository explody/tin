
import re
import requests
import simplejson as json
from six import iteritems

from . import ApeyeConfig

import pprint

class ApeyeError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
        
class ApeyeObjectNotFound(ApeyeError):

    def __init__(self, value):
        super(ApeyeObjectNotFound, self).__init__(value)

class ApeyeInvalidArgs(Exception):

    def __init__(self, value):
        super(ApeyeInvalidArgs, self).__init__(value)


class ApeyeApiClass(object):

    def __init__(self):
        self._methods = []

    def __repr__(self):
        return type(self).__name__

    def register_method(self, name):
        self._methods.append(name)

    def methods(self):
        return [getattr(self, mth) for mth in self._methods]


class HTTPGenericHeaderAuth(requests.auth.AuthBase):

    def __init__(self, headers):
        self.headers = headers

    def __call__(self, r):
        r.headers.update(self.headers)
        return r

class HTTPGenericParameterAuth(requests.auth.AuthBase):

    def __init__(self, params):
        self.params = params

    def __call__(self, r):
        r.params.update(self.headers)
        return r

class ApeyeApiMethod(object):

    def __init__(self, apiobj, clsobj, name, method_data):

        self.name = name
        self.api = apiobj
        self.cls = clsobj
        self.method_data = method_data

        if 'public' in method_data:
            self.public = method_data['public']
        else:
            self.public = False

        self.method = method_data['method']
        self.path = method_data['path']

        # If the method specifies an expected return code, grab it, otherwise
        # default to 200
        if 'return' in method_data:
            self.expect_return = method_data['return']
        else:
            self.expect_return = 200

        # Here, we handle parameters defined as 'must' or 'may'
        self.must = []
        self.may = []
        self.default_params = {}
        self.default_tokens = {}

        if hasattr(self.api.conf, 'params'):
            self.may += self.api.conf.params.get('may',[])
            self.must += self.api.conf.params.get('must',[])

        if 'must' in self.method_data:
            self.must = self.method_data['must']

        if 'may' in self.method_data:
            self.may += self.method_data['may']

        # Start with default parameters for the api and method, if they exist
        if hasattr(self.api.conf, 'default_params'):
            self.default_params.update(self.api.conf.default_params)

        if 'default_params' in self.method_data:
            self.default_params.update(self.method_data['default_params'])
            self.may += self.method_data['default_params']

        # Start with default path tokens for the api and method, if they exist
        if hasattr(self.api.conf, 'default_tokens'):
            self.default_tokens.update(self.api.conf.default_tokens)

        if 'default_tokens' in self.method_data:
            self.default_tokens.update(self.method_data['default_tokens'])

        self.may = list(set(self.may))
        self.must = list(set(self.must))

        self.url = "%s://%s:%s%s%s" % (self.api.conf.scheme,
                                       self.api.conf.host,
                                       self.api.conf.port,
                                       self.api.conf.basepath,
                                       method_data['path'])


    def to_json(self):

        return json.dumps({
            'scheme': self.scheme,
            'host': self.host,
            'port': self.port,
            'credentials': self.creds,
            'url': self.url,
            'method_data': self.method_data
        })

    def path_tokens(self):

        tokenre = re.compile(':([a-zA-Z0-9_]+)')
        return tokenre.findall(self.path)

    def __repr__(self):

        return '%s.%s.%s' % (self.api.conf.api_name, self.cls, self.name)

    def __call__(self, id=None, **kwargs):

        # This is where we can put validations on the kwargs,
        # based off data in api.yml (not there yet)

        url = self.url
        data = {}
        params = self.default_params.copy()
        tokens = self.default_tokens.copy()

        # Overwrite with provided arguments. Pop the value out of kwargs.
        if 'params' in kwargs:
            params.update(kwargs.pop('params'))

        # No defaults for data.
        if 'data' in kwargs:
            data = kwargs.pop('data')
        else:
            data = None
        
        # If 'id' is passed as a positional, it overrides 'id' as a kwarg
        if id is not None:
            kwargs['id'] = id

        # The remaining kwargs *should* correspond to path tokens
        # Merge with defaults, if they exist
        tokens.update(kwargs)

        # Ensure all our path tokens are accounted for
        for tok in self.path_tokens():
            if tok not in tokens:
                raise ApeyeInvalidArgs("%s called with missing token "
                                       "argument %s. For path %s" %
                                       (self, tok, self.path))

        # Presence of our path tokens is verified. Replace them in our url
        for k, v in iteritems(tokens):
            url = url.replace(':%s' % k, str(v))

        try:
            resp = None
            response_count = {}
            while True:
                if self.method == "GET":
                    r = requests.get(url, headers=self.api.conf.headers,
                                     auth=self.api.auth(), 
                                     verify=self.api.conf.ssl['verify'],
                                     params=params)
                elif self.method == "OPTIONS":
                    r = requests.options(url, headers=self.api.conf.headers,
                                     auth=self.api.auth(), 
                                     verify=self.api.conf.ssl['verify'],
                                     params=params)
                elif self.method == "POST":
                    r = requests.post(url, data=json.dumps(data),
                                      headers=self.api.conf.headers,
                                      auth=self.api.auth(), 
                                      verify=self.api.conf.ssl['verify'],
                                      params=params)
                elif self.method == "PATCH":
                    r = requests.patch(url, data=json.dumps(data),
                                      headers=self.api.conf.headers,
                                      auth=self.api.auth(), 
                                      verify=self.api.conf.ssl['verify'],
                                      params=params)
                elif self.method == "PUT":
                    r = requests.put(url, data=json.dumps(data),
                                     headers=self.api.conf.headers,
                                     auth=self.api.auth(), 
                                     verify=self.api.conf.ssl['verify'],
                                     params=params)
                elif self.method == "DELETE":
                    r = requests.delete(url, data=json.dumps(data),
                                        headers=self.api.conf.headers,
                                        auth=self.api.auth(), 
                                        verify=self.api.conf.ssl['verify'],
                                        params=params)

                if r.status_code == 404:
                    raise ApeyeObjectNotFound("Object not found. Tried: %s. "
                                              "Apeye says: %s" %
                                              (url, r.text))
                elif r.status_code != self.expect_return:
                    raise ApeyeError("ERROR at %s Apeye says: %s" %
                                     (url, r.text))

                try:
                    thisresp = r.json()
                except Exception as e:
                    raise ApeyeError("ERROR decoding response JSON. "
                                     "Raw response is: %s" % r.text)

                if isinstance(resp, list):
                    resp.extend(thisresp)
                elif isinstance(resp, dict):
                    resp.update(thisresp)
                else:
                    resp = thisresp
                
                # Handle pagination types
                
                # "header_count" expects a total passed over in the HTTP header
                # 
                if ((hasattr(self.api.conf, 'pagination')) and
                    (self.api.conf.pagination['type'] == 'header_count')):
                    header_count = r.headers.get(
                        self.api.conf.pagination['header'], "0"
                    ) # if the specified header doesn't exist, assume 0 addt'l pages
                    
                    response_count['current'] = len(thisresp)
                    response_count['total'] = len(resp)
                    
                    # If we haven't fetched all the records, set the config'd
                    # path or params then continue
                    if response_count['total'] < int(header_count):
                        
                        v = self.api.conf.pagination['value']
                        
                        if 'param' in self.api.conf.pagination:
                            p = self.api.conf.pagination['param']
                            params[p] = response_count[v]
                        elif 'path' in self.api.conf.pagination:
                            n = self.api.conf.pagination['path']
                            path = n % response_count[v]
                            url = '%s/%s' % (url, path)
                    else:
                        break
                    
                else:
                    if 'next' not in r.links:
                        break
                    else:
                        url = r.links['next']['url']

        except requests.exceptions.HTTPError as e:
            raise ApeyeError("ERROR: %s" % e)

        return resp


class ApeyeApi(object):

    def __init__(self, **kwargs):

        self.conf = ApeyeConfig(**kwargs)
        self._classes = []

        # loop through the classes in okta-api.yml
        for cls, mths in iteritems(self.conf.apidata['classes']):
      
            # Each top level class name will be an ApeyeApiClass
            new_type = type(cls, (ApeyeApiClass,), {})
            new_cls = new_type()

            # For each defined method, add an ApeyeApiMethod as
            # an attribute in the ApeyeApiClass instance
            for mth, data in iteritems(mths):
                setattr(new_cls, mth, ApeyeApiMethod(self, new_cls, mth, data))
                new_cls.register_method(mth)

            setattr(self, cls, new_cls)
            self._classes.append(cls)

    def auth(self):

        if self.conf.authtype == 'basic':

            u = self.conf.credentials.get('username', None)
            p = self.conf.credentials.get('password', None)
            return requests.auth.HTTPBasicAuth(u, p)

        elif self.conf.authtype == 'header':

            return HTTPGenericHeaderAuth(self.conf.credentials)

        elif self.conf.authtype == 'param':

            return HTTPGenericParameterAuth(self.conf.credentials)

    def classes(self):

        return [getattr(self, cls) for cls in self._classes]

    def methods(self):
        mths = []
        for cls in self.classes():
            for mth in cls.methods():
                mths.append(mth)

        return mths
