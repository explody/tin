import os
import sys
import yaml
import logging
import simplejson as json
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
             os.path.expanduser('~'),
             os.path.expanduser('~/.apeye')]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApeyeError(Exception):
    """Generic Apeye exception"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ApeyeConfigNotFound(Exception):
    """Config file not found exception"""

    def __init__(self, filename, paths):
        self.value = "Not found: [" + filename + "] I looked here:" + \
                     " ".join(paths)

    def __str__(self):
        return self.value


class ApeyeConfig(object):
    """Class which represents the configuration of the API

    Configuration will be loaded from a YAML or JSON file, which may have different environments
    defined, each with their own settings.  Upon parsing, the config key->values will be stored
    as object attributes.

    Args:
        conffile (str): Relative or absolute path to the YAML or JSON config file
        environ (str): Name of the environment to load

    Attributes:
        confpaths (list): List of strings of paths in which to find the conffile. Defined above.
        confpath (str): Final file path of the config file
    """

    def __init__(self, conffile='apeye.yml', environ='development'):

        if 'APEYE_ENV' in os.environ:
            apeye_env = os.environ['APEYE_ENV']
        else:
            apeye_env = environ

        self.confpaths = confpaths
        self.confpath = self.find_config(conffile)
        logger.info("Using config: % s Environment: %s" % (self.confpath, environ))
        fh = open(self.confpath, "rb")
        conf = yaml.load(fh.read())

        # Add the directory of the file we just loaded to confpaths
        self.confpaths.append(os.path.dirname(os.path.abspath(self.confpath)))

        if apeye_env not in conf['environments']:
            raise ApeyeError("No such environment is configured: %s" %
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
            self.credentials = self._loadfile(self.find_config(self.credfile))

        # noinspection PyUnresolvedReferences
        apifile = self.find_config(self.apifile)
        self.apidata = self._loadfile(apifile)

    def _loadfile(self, fpath):
        """Parses the conf file as YAML or JSON based on file extension

        Arguments:
            fpath (str): Path to the file

        Returns
            dict: Contents of the file parsed to a dict
        """

        fh = open(fpath, "rb")
        if fpath.endswith('.yml'):
            return yaml.load(fh.read())
        elif fpath.endswith('.json'):
            return json.loads(fh.read())

    def set(self, key, value):
        """Config attribute setter

        Arguments:
            key (str): Name of the attribute
            value (str): Value to set. Presumed to be a string but this isn't enforced.
        """

        setattr(self, key, value)

    def get(self, key):
        """Config attribute getter

        Arguments:
            key (str): Name of the attribute

        Returns:
            The value of the attribute
        """
        return getattr(self, key)

    def find_config(self, filename):
        """Searches the confpaths for the given config file

        Arguments:
            filename (str): The absolute or relative path to the file"
        """
        
        # expanduser here in case someone passed a "~" path
        filename = os.path.expanduser(filename)

        if os.path.isfile(filename):
            return os.path.abspath(filename)

        for path in self.confpaths:
            confpath = os.path.join(path, filename)
            if os.path.isfile(confpath):
                return confpath

        raise ApeyeConfigNotFound(filename, self.confpaths)
