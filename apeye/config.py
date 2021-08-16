import logging
import os
import simplejson as json
import sys
import yaml

from apeye.exceptions import ApeyeConfigNotFound, ApeyeError

DEFAULTS = {"scheme": "https", "port": 443}

# We only do JSON APIs right now
DEFAULT_TYPE = "application/json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ApeyeConfig(object):
    """Class which represents the configuration of the API

    Configuration will be loaded from a YAML or JSON file, which may have different environments
    defined, each with their own settings.  Upon parsing, the config key->values will be stored
    as object attributes.

    Args:
        config_file (str): Relative or absolute path to the YAML or JSON config file
        environment (str): Name of the environment to load

    Attributes:
        confpaths (list): List of strings of paths in which to find the config_file. Defined above.
        confpath (str): Final file path of the config file
    """

    def __init__(self, config_file=None, environment=None):

        if config_file is None:
            if 'APEYE_CONFIG' in os.environ:
                config_file = os.environ.get('APEYE_CONFIG')
            else:
                raise ApeyeError("Config file cannot be None")

        if environment is None:
            if 'APEYE_ENV' in os.environ:
                environment = os.environ.get('APEYE_ENV')
            else:
                raise ApeyeError("Environment cannot be None")

        print("ENV", environment)
        print("FILE", config_file)

        self.config_file = self.find_config(config_file)
        self.config_dir = os.path.dirname(self.config_file)

        logger.info("Using config: % s Environment: %s" % (self.config_file, environment))

        conf = self._loadfile(self.config_file)

        if conf is None:
            raise ApeyeError("Invalid config (empty?)")

        if environment not in conf.get("environments", {}):
            raise ApeyeError("No such environment is configured: {}".format(environment))

        self._api_attrs = conf.get("common", {})
        self.headers = {
            "Content-type": self._api_attrs["type"]
            if self._api_attrs.get("type", False)
            else DEFAULT_TYPE,
            "Accept": self._api_attrs["type"]
            if self._api_attrs.get("type", False)
            else DEFAULT_TYPE,
        }

        if "headers" in self._api_attrs:
            self.headers.update(self._api_attrs["headers"])

        self.set("use_session", conf.get("use_session", True))

        env_attrs = conf["environments"][environment]

        self.api_name = os.path.splitext(os.path.basename(self.config_file))[0]

        self._api_attrs.update(env_attrs)

        # Set toplevel keys in the yaml as attributes on this object
        for k, v in self._api_attrs.items():
            setattr(self, k, v)

        if self.credfile:
            self.credentials = self._loadfile(self.find_config(self.credfile))

        self.apifile = self.find_config(self.apifile)
        self.apidata = self._loadfile(self.apifile)

        if "modelfile" in self._api_attrs:
            self.modelfile = self.find_config(self.modelfile)
            self.models = self._loadfile(self.modelfile)
        else:
            self.models = {}

    def _loadfile(self, filepath):
        """Parses the conf file as YAML or JSON based on file extension

        Arguments:
            fpath (str): Path to the file

        Returns
            dict: Contents of the file parsed to a dict
        """
        with open(filepath, "rb") as fh:
            if filepath.endswith(".yml"):
                return yaml.safe_load(fh.read())
            elif filepath.endswith(".json"):
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
        try:
            return getattr(self, key)
        except AttributeError as e:
            return None

    def find_config(self, filename):
        """Takes the given path to a config file, ensures it exists, and returns an absolute
        path.

        Arguments:
            filename (str): The absolute or relative path to the file"
        """

        # expanduser here in case someone passed a "~" path
        filename = os.path.expanduser(filename)

        if os.path.isabs(filename):
            return filename
        else:
            if getattr(self, 'config_dir', None):
                file_in_config_dir = os.path.join(self.config_dir, filename)
                if os.path.isfile(file_in_config_dir):
                    return os.path.abspath(file_in_config_dir)

            if os.path.isfile(filename):
                return os.path.abspath(filename)

        raise ApeyeConfigNotFound(filename)
