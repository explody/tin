import logging
import os
import simplejson as json
import yaml

from deepmerge import always_merger
from tin.exceptions import TinConfigNotFound, TinError

import pprint
import sys

DEFAULTS = {
    "scheme": "https",
    "port": 443,
    "use_session": True,
    "ssl": {
        "verify": True
    }
}

# We only do JSON APIs right now
DEFAULT_CONTENT_TYPE = "application/json"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TinConfig(object):
    """Class which represents the configuration of an API

    Configuration can be loaded from a YAML or JSON file, from YAML or JSON in environment vars, or directly from environment vars.

    Configuration has an order of precedence for loading data:

        1. config file path passed as an argument
        2. config file path from the TIN_CONFIG env var
        3. config data as JSON from the TIN_CONFIG env var
        4. config data as YAML from the TIN_CONFIG env var

    Configurations may be organized in as multi-environment or single environment.

    Multi-environment configs look like

    ```yaml
    ---
    environments:
      myenv:
        key: value
    common:
      key: value
    ```

    Whereas single environment configs look like
    ```yaml
    key: value
    otherkey: othervalue
    ```

    Aftr config data is loaded, environment variables will be loaded, which will override config file values if set.

    For multi-environment configs, the first key is the environment name. Note the double underscores.
    TIN__BASIC__HOST corresponds to config_data['environments']['basic']['host']

    Common vars are similar

    TIN__COMMON__BASEPATH corresponds to config_data['common']['basepath']

    In single-environment configs, env vars still use double underscores, but without environment name or "COMMON":

    TIN__HOST corresponds to config_data['host']

    And so on.  This also leaves open the possiblity of loading the entire
    config from individual env vars

    Args:
        config_file (str): Relative or absolute path to the YAML or JSON config file
        environment (str): Optional name of the API environment to load

    """

    def __init__(self, config_file=None, environment=None):

        self.api_name = None
        self.config_src = None
        self.config_dir = None
        self.config_data = None
        self.environment = None

        # Environment is required regardless of where config data comes from
        if environment is None:
            if "TIN_ENV" in os.environ:
                self.environment = os.environ.get("TIN_ENV")
            else:
                self.environment = None
        else:
            self.environment = environment

        ######################
        # Config loading
        # Handle being passed config data from the environment, as a file or as JSON or
        # YAML, if a config file path was not given.
        if config_file is None:
            if "TIN_CONFIG" in os.environ:
                config = os.environ.get("TIN_CONFIG")
                if os.path.isfile(config):
                    config_data = self._load_main_config_from_file(config)
                else:
                    try:
                        config_data = self._load_json_or_yaml(config)
                    except ValueError:
                        # Don't die here, as we might load config from individual env
                        # vars
                        config_data = {}
                    self.config_src = 'ENV'
            else:
                config_data = {}
                self.config_src = 'ENV'
        else:
            config_data = self._load_main_config_from_file(config_file)

        logger.info(
            "Using config: {} Environment: {}".format(self.config_src, self.environment if self.environment else 'default (none)')
        )

        ######################
        # Load from environment variables
        # Update from env vars as described above
        self.config_data = self._update_from_env(config_data, environment)

        if not self.config_data:
            raise TinError("Empty config!")

        # If we have an an environment based config, but no environment OR
        # an environment was specifid but we still don't have environment data, it's
        # a problem
        if self.environment is None and "environments" in self.config_data:
            raise TinError("I have an environment-based config"
                           "but environment is None")
        elif self.environment is not None and self.environment not in self.config_data.get("environments", {}):
            raise TinError("Environment set but not found in config: {}".format(self.environment))

        if self.config_data.get('api_name', None):
            self.api_name = self.config_data['api_name']
        elif self.config_data.get('common', {}).get('api_name', None):
            self.api_name = self.config_data['common']['api_name']
        elif os.path.isfile(self.config_src):
            self.api_name = os.path.splitext(os.path.basename(self.config_src))[0]
        else:
            TinError("""Cannot determine the API name Either set TIN__API_NAME env
                        var or set 'api_name' in the common settings.""")

        if self.environment:
            # Merge common env config into global defaults
            self._api_config = always_merger.merge(
                DEFAULTS,
                self.config_data.get("common", {})
            )
            # Now merge env-specific settings into that
            self._api_config = always_merger.merge(
                self._api_config,
                self.config_data["environments"][self.environment]
            )
        else:
            # If there's no environment, all the config keys should already be top-level
            self._api_config = self.config_data

        ######################
        # Credentials
        if self.config_data.get('auth_type') in [None, 'none']:
            self.credentials = None
        elif os.path.isfile(self.config_data.get('credentials', '/')):
            self.credentials = self._loadfile(self.find_config(self.config_data['credentials']))
        else:
            try:
                self.credentials = self._load_json_or_yaml(self.config_data['credentials'])
            except ValueError:
                # doesn't load as json or yaml, may be a custom string
                self.credentials = self.config_data['credentials']

        ######################
        # Headers
        self.headers = {
            "Content-type": self._api_config.get("content_type", False) or DEFAULT_CONTENT_TYPE,
            "Accept": self._api_config.get("content_type", False) or DEFAULT_CONTENT_TYPE,
        }

        # Merge in any headers from the config
        if "headers" in self._api_config:
            self.headers.update(self._api_config["headers"])

        # Set toplevel keys in the yaml as attributes on this object
        for k, v in self._api_config.items():
            setattr(self, k, v)

        ######################
        # Additional file-based configs
        # API and Model configs must be files
        self.apidata = self._load_config_from_file(self.api_file)

        if "model_file" in self._api_config:
            self.models = self._load_config_from_file(self.model_file)
        else:
            self.models = {}

    def _update_from_env(self, config_data, environment=None):
        """Read configuration from environment variables

        Reads config keys and values from env vars following a particular naming scheme:

        TIN__<ENVIRONMENT|KEY>__<KEY>.. = <VALUE>

        See the class docs for more detail.

        Arguments:
            config_data (dict): A dict into which keys and values will be loaded
            environment (string|None): Optional environment name

        Returns:
            see _loadfile()
        """
        for var, val in os.environ.items():
            if var.startswith('TIN__{}'.format(environment if environment else '')):
                env_parts = [v.lower() for v in var.split('__')[1:]]
                dict_from_list = current = {}
                # Some confusing iteration that turns a list into nested dict keys
                for i in range(0, len(env_parts)):
                    part = env_parts[i]
                    if i == len(env_parts)-1:
                        current[part] = val
                    else:
                        current[part] = {}
                    current = current[part]

                config_data = always_merger.merge(config_data, dict_from_list)

        return config_data

    def _load_config_from_file(self, filename):
        """Load an arbitrary configuration from a file.

        Update config_src and api_name.

        Arguments:
            filename (str): Relative or absolute path to a file

        Returns:
            see _loadfile()
        """

        return self._loadfile(self.find_config(filename))


    def _load_main_config_from_file(self, filename):
        """Load main configuration from a file.

        Update config_src and config_dir.

        Arguments:
            filename (str): Relative or absolute path to a file

        Returns:
            see _loadfile()
        """
        self.config_src = self.find_config(filename)
        self.config_dir = os.path.dirname(os.path.abspath(filename))
        return self._load_config_from_file(self.config_src)


    def _loadfile(self, filepath):
        """Parses the conf file as YAML or JSON based on file extension

        Arguments:
            filepath (str): Path to the file

        Returns
            dict: Contents of the file parsed to a dict
        """
        with open(filepath, "rb") as fh:
            if filepath.endswith(".yml") or filepath.endswith(".yaml"):
                return yaml.safe_load(fh.read())
            elif filepath.endswith(".json"):
                return json.loads(fh.read())


    def _load_json_or_yaml(self, data):
        """Given a chunk of data, attempts to load it as JSON or YAML, in that order

        Arguments:
            data (str): Data presumed to be JSON or YAML

        Returns
            dict: The data parsed to a dict
        """
        try:
            loaded = json.loads(data)
        except json.decoder.JSONDecodeError:
            # Explicitly making this a dict works around the fact that
            # pyyaml will load a single plain string without error
            loaded = dict(yaml.safe_load(data))

        return loaded


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
        except AttributeError:
            return None

    def find_config(self, filename):
        """Takes the given path to a config file, ensures it exists, and returns an
            absolute path.

        Arguments:
            filename (str): The absolute or relative path to the file"
        """

        # expanduser here in case someone passed a "~" path
        filename = os.path.expanduser(filename)
        if os.path.isabs(filename):
            return filename
        else:
            if getattr(self, "config_dir", None):
                file_in_config_dir = os.path.join(self.config_dir, filename)
                if os.path.isfile(file_in_config_dir):
                    return os.path.abspath(file_in_config_dir)

            if os.path.isfile(filename):
                return os.path.abspath(filename)

        raise TinConfigNotFound(filename)
