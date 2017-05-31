import os
import sys
import yaml
import logging
from six import iteritems

from .version import VERSION

__version__ = VERSION

DEFAULTS = {'scheme': 'https',
            'port': 443}

# We only do JSON APIs right now
DEFAULT_TYPE = 'application/json'
                   
# Paths to check, in order
#   calling script directory
#   module directory
#   user home directory
confpaths = [os.path.dirname(os.path.realpath(sys.argv[0])),
             os.path.dirname(os.path.realpath(__file__)),
             os.path.expanduser('~')]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApeyeException(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ApeyeConfigNotFound(Exception):

    def __init__(self, filename, paths):
        self.value = "Not found: [" + filename + "] I looked here:" + \
                     " ".join(paths)

    def __str__(self):
        return self.value


class ApeyeConfig(object):

    def __init__(self, conffile='apeye.yml', environ='development'):

        if 'APEYE_ENV' in os.environ:
            apeye_env = os.environ['APEYE_ENV']
        else:
            apeye_env = environ

        self.confpaths = confpaths
        self.confpath = self.find_config(conffile)
        fh = open(self.confpath, "rb")
        conf = yaml.load(fh.read())

        # Add the directory of the file we just loaded to confpaths
        self.confpaths.append(os.path.dirname(os.path.abspath(self.confpath)))

        if apeye_env not in conf['environments']:
            raise ApeyeException("No such environment is configured: %s" %
                                 apeye_env)

        self._api_attrs = conf.get('common', {})
        self.headers = {'Content-type': self._api_attrs['type'] if 
                                        self._api_attrs.get('type', False) else 
                                        DEFAULT_TYPE,
                        'Accept': self._api_attrs['type'] if 
                                  self._api_attrs.get('type', False) else 
                                  DEFAULT_TYPE} 

        if 'headers' in conf:
            self.headers.update(conf['headers'])

        env_attrs = conf['environments'][apeye_env]

        self.api_name = os.path.splitext(os.path.basename(self.confpath))[0]

        self._api_attrs.update(env_attrs)

        for k, v in iteritems(self._api_attrs):
            setattr(self, k, v)

        # noinspection PyUnresolvedReferences
        if self.credfile:
            self.credfile = self.find_config(self.credfile)
            self.credentials = yaml.load(open(self.credfile, "rb").read())

        # noinspection PyUnresolvedReferences
        objfile = self.find_config(self.objfile)
        ofh = open(objfile, "rb")
        self.objdata = yaml.load(ofh.read())

        # noinspection PyUnresolvedReferences
        apifile = self.find_config(self.apifile)
        afh = open(apifile, "rb")
        self.apidata = yaml.load(afh.read())

    def set(self, key, value):

        setattr(self, key, value)

    def get(self, key):

        return getattr(self, key)

    def find_config(self, filename):

        # expanduser here in case someone passed a "~" path
        filename = os.path.expanduser(filename)

        if os.path.isfile(filename):
            return os.path.abspath(filename)

        for path in self.confpaths:
            confpath = os.path.join(path, filename)
            if os.path.isfile(confpath):
                return confpath

        raise ApeyeConfigNotFound(filename, self.confpaths)
