"""Tin is a thin, configurable wrapper around requests, to interact with
REST APIs that speak JSON.
"""

from .api import TinApi
from .config import TinConfig
from .version import VERSION

__version__ = VERSION
