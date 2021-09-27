import logging
import os
import simplejson as json
import yaml

from deepmerge import always_merger
from tin.exceptions import TinConfigNotFound, TinError


# We only do JSON APIs right now
DEFAULT_CONTENT_TYPE = "application/json"

DEFAULTS = {
    "scheme": "https",
    "port": 443,
    "use_session": True,
    "ssl": {"verify": True},
    "content_type": DEFAULT_CONTENT_TYPE,
    "auth_type": "basic",
}


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

    For multi-environment configs, the first key must always be 'ENVIRONMENTS'. Note the double underscores.
    TIN__ENVIRONMENTS__BASIC__HOST corresponds to config_data['environments']['basic']['host']

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

    def __init__(self, config_file=None, environment=None, env_prefix=None):

        self.api_name = None
        self.config_src = None
        self.config_dir = None
        self.config_data = None
        self.environment = None

        self._api_config = dict(DEFAULTS)

        ######################
        # Env prefix
        if env_prefix:
            self._env_prefix = "TIN_{}".format(env_prefix).upper()
        else:
            self._env_prefix = "TIN"

        # Environment is required regardless of where config data comes from
        if environment is None:
            if f"{self._env_prefix}_ENV" in os.environ:
                self.environment = os.environ.get(f"{self._env_prefix}_ENV")
            else:
                self.environment = None
        else:
            self.environment = environment

        ######################
        # Config loading
        # Handle being passed config data from the environment, as a file or as JSON or
        # YAML, if a config file path was not given.
        if config_file is None:
            if f"{self._env_prefix}_CONFIG" in os.environ:
                config = os.environ.get(f"{self._env_prefix}_CONFIG")
                if os.path.isfile(config):
                    config_data = self._load_main_config_from_file(config)
                else:
                    try:
                        config_data = self._load_json_or_yaml(config)
                    except ValueError:
                        # Don't die here, as we might load config from individual env
                        # vars
                        config_data = {}
                    self.config_src = "ENV"
            else:
                config_data = {}
                self.config_src = "ENV"
        else:
            config_data = self._load_main_config_from_file(config_file)

        logger.info(
            "Using config: {} Environment: {}".format(
                self.config_src,
                self.environment if self.environment else "default (none)",
            )
        )

        ######################
        # Load from environment variables
        # Update from env vars as described above
        self.config_data = self._update_from_env(config_data, environment)

        if not self.config_data:
            raise TinError("Empty config!")

        # If we have an an environment based config, but no environment OR
        # an environment was specified but we still don't have environment data, it's
        # a problem
        if self.environment is None and "environments" in self.config_data:
            raise TinError("I have an environment-based config but environment is None")
        elif (
            self.environment is not None
            and self.environment not in self.config_data.get("environments", {})
        ):
            raise TinError(
                "Environment set but not found in config: {}".format(self.environment)
            )

        ######################
        # Determine API name for type naming
        if self.config_data.get("api_name", None):
            self.api_name = self.config_data["api_name"]
        elif self.config_data.get("common", {}).get("api_name", None):
            self.api_name = self.config_data["common"]["api_name"]
        elif os.path.isfile(self.config_src):
            self.api_name = os.path.splitext(os.path.basename(self.config_src))[0]
        else:
            raise TinError(
                """Cannot determine the API name! Either set TIN__API_NAME env
                        var or set 'api_name' in the common settings."""
            )

        ######################
        # Build the final _api_config
        if self.environment:
            # Merge common env config into _api_config
            self._api_config = always_merger.merge(
                self._api_config, self.config_data.get("common", {})
            )

            # Now merge env-specific settings into that result
            self._api_config = always_merger.merge(
                self._api_config, self.config_data["environments"][self.environment]
            )
        else:
            # If there's no environment, all the config keys should already be top-level
            self._api_config = always_merger.merge(self._api_config, self.config_data)

        # At this point, we must have an api_file or there's no point in continuing
        if self._api_config.get("api_file", None) is None:
            raise TinError("No api_file specified in the config. Cannot continue.")

        ######################
        # Determine a config_dir, if any
        if "config_dir" not in self._api_config and self.config_src != "ENV":
            # If config_dir is in the api_config, it will be accessible via
            # self.config_dir already due to __getattr__. If not, set it based on
            # the main config path *IF* there is one
            self._api_config["config_dir"] = os.path.dirname(
                os.path.abspath(self.config_src)
            )
            self.config_dir = self._api_config["config_dir"]
        elif "config_dir" in self._api_config:
            self.config_dir = self._api_config["config_dir"]

        ######################
        # Credentials
        if (
            self._api_config.get("auth_type") in [None, "none"]
            or "credentials" not in self._api_config
        ):
            # If auth_type is None, set credentials to None, otherwise, if auth_type is set
            # but credentials are absent, continue instead of dying as creds may be set after
            # instantiation
            self._api_config["credentials"] = None
        else:
            try:
                self.credentials = self._load_config_from_file(
                    self._api_config["credentials"]
                )
            except TinConfigNotFound:
                self.credentials = self._load_json_or_yaml(
                    self._api_config["credentials"]
                )
            except ValueError:
                # doesn't load as json or yaml, may be a custom string
                self.credentials = self._api_config["credentials"]

        ######################
        # Headers
        self.headers = {
            "Content-type": self._api_config.get("content_type", False)
            or DEFAULT_CONTENT_TYPE,
            "Accept": self._api_config.get("content_type", False)
            or DEFAULT_CONTENT_TYPE,
        }

        # Merge in any headers from the config
        if self._api_config.get("headers", None) is not None:
            self.headers.update(self._api_config["headers"])

        ######################
        # Minor data checks
        try:
            self._api_config["port"] = int(self._api_config["port"])
        except ValueError:
            raise TinError("Invalid port, must be an integer")

        ######################
        # Additional file-based configs
        # API and Model configs must be files
        self.apidata = self._load_config_from_file(self.api_file)

        self.models = (
            self._load_config_from_file(self._api_config.get("model_file", None))
            if "model_file" in self._api_config
            else {}
        )

    def _update_from_env(self, config_data, environment=None):
        """Read configuration from environment variables

        Reads config keys and values from env vars following a particular naming scheme:

        TIN__[ENVIRONMENTS__]<ENVIRONMENT|KEY>__<KEY>.. = <VALUE>

        See the class docs for more detail.

        Arguments:
            config_data (dict): A dict into which keys and values will be loaded
            environment (string|None): Optional environment name

        Returns:
            see _loadfile()
        """
        for var, val in os.environ.items():
            if var.startswith(
                "{}__{}".format(
                    self._env_prefix,
                    "ENVIRONMENTS__{}".format(environment.upper())
                    if environment is not None
                    else "",
                )
            ):
                env_parts = [v.lower() for v in var.split("__")[1:]]
                dict_from_list = current = {}
                # Some confusing iteration that turns a list into nested dict keys
                for i in range(0, len(env_parts)):
                    part = env_parts[i]
                    if i == len(env_parts) - 1:
                        current[part] = val
                    else:
                        current[part] = {}
                    current = current[part]

                config_data = always_merger.merge(config_data, dict_from_list)

        return config_data

    def __getattr__(self, item):
        """Look up referenced attrs in _api_config before __dict__

        Arguments:
            item (str): attr or method name

        Returns:
            Value of the attribute key
        """
        if item in self._api_config:
            return self._api_config[item]
        elif item in self.__dict__:
            return self.__dict__[item]
        else:
            self.method_missing(item)

    def method_missing(self, method_name, *args, **kwargs):
        """Handle references to missing attrs

        Arguments:
            method_name (str): Name of referenced attr

        Raises:
            AttributeError
        """
        e = "type object '%s' has no attribute '%s'" % (
            self.__class__.__name__,
            method_name,
        )
        raise AttributeError(e)

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

        Update config_src.

        Arguments:
            filename (str): Relative or absolute path to a file

        Returns:
            see _loadfile()
        """
        self.config_src = self.find_config(filename)
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

        self._api_config[key] = value

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

    @property
    def credentials(self):
        """Credentials property

        Arguments:
            None
        """

        return self._api_config.get('credentials', None)

    @credentials.setter
    def credentials(self, value):
        """Credentials setter

        Arguments:
            value (any): The value to assign to credentials
        """

        self._api_config['credentials'] = value

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
            if self.config_dir is not None:
                # self.config_dir is either None or an abspath already
                filename = os.path.join(self.config_dir, filename)
                if os.path.isfile(filename):
                    return filename
            elif os.path.isfile(filename):
                return os.path.abspath(filename)

        raise TinConfigNotFound(filename)
