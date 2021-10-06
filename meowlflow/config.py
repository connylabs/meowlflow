"""
Acquire runtime configuration from environment variables (etc).
"""

import os
from pathlib import Path
import yaml


def logfile_path(jsonfmt=False, debug=False):
    """
    Returns the a logfileconf path following this rules:
      - conf/logging_debug_json.conf # jsonfmt=true,  debug=true
      - conf/logging_json.conf       # jsonfmt=true,  debug=false
      - conf/logging_debug.conf      # jsonfmt=false, debug=true
      - conf/logging.conf            # jsonfmt=false, debug=false
    Can be parametrized via envvars: JSONLOG=true, DEBUGLOG=true
    """
    _json = ""
    _debug = ""

    if jsonfmt or os.getenv("JSONLOG", "false").lower() == "true":
        _json = "_json"

    if debug or os.getenv("DEBUGLOG", "false").lower() == "true":
        _debug = "_debug"

    return os.path.join(MEOWLFLOW_CONF_DIR, "logging%s%s.conf" % (_debug, _json))


def getenv(name, default=None, convert=str):
    """
    Fetch variables from environment and convert to given type.

    Python's `os.getenv` returns string and requires string default.
    This allows for varying types to be interpolated from the environment.
    """

    # because os.getenv requires string default.
    internal_default = "$(none)$"
    val = os.getenv(name, internal_default)

    if val == internal_default:
        return default

    if callable(convert):
        return convert(val)

    return val


def envbool(value: str):
    return value and (value.lower() in ("1", "true"))


APP_ENVIRON = getenv("APP_ENV", "development")

MEOWLFLOW_API = getenv("MEOWLFLOW_API", "https://meowlflow.conny.dev")
MEOWLFLOW_SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
MEOWLFLOW_ROOT_DIR = os.path.abspath(os.path.join(MEOWLFLOW_SOURCE_DIR, "../"))
MEOWLFLOW_CONF_DIR = os.getenv(
    "MEOWLFLOW_CONF_DIR", os.path.join(MEOWLFLOW_ROOT_DIR, "conf/")
)
MEOWLFLOW_CONF_FILE = os.getenv("MEOWLFLOW_CONF_FILE", None)
MEOWLFLOW_DOWNLOAD_DIR = os.getenv("MEOWLFLOW_DOWNLOAD_DIR", "/tmp/meowlflow")
MEOWLFLOW_TOKEN = os.getenv(
    "MEOWLFLOW_TOKEN", "changeme"
)  # Set to None or empty to skip the token

MEOWLFLOW_TMP_DIR = os.getenv("MEOWLFLOW_TMP_DIR", "/tmp/meowlflow")
MEOWLFLOW_SENTRY_URL = os.getenv("MEOWLFLOW_SENTRY_URL", None)
MEOWLFLOW_SENTRY_ENV = os.getenv("MEOWLFLOW_SENTRY_ENV", "development")

PROMETHEUS_MULTIPROC_DIR = os.getenv(
    "PROMETHEUS_MULTIPROC_DIR", os.path.join(MEOWLFLOW_TMP_DIR, "prometheus")
)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = PROMETHEUS_MULTIPROC_DIR


class MeowlflowConfig:
    """
    Class to initialize the projects settings
    """

    def __init__(self, defaults=None, confpath=None):
        self.settings = {
            "meowlflow": {
                "debug": False,
                "env": APP_ENVIRON,
                "url": MEOWLFLOW_API,
                "download_dir": MEOWLFLOW_DOWNLOAD_DIR,
                "token": MEOWLFLOW_TOKEN,
                "tmp_dir": MEOWLFLOW_TMP_DIR,
                "prometheus_dir": PROMETHEUS_MULTIPROC_DIR,
            },
            "sentry": {
                "url": MEOWLFLOW_SENTRY_URL,
                "environment": MEOWLFLOW_SENTRY_ENV,
            },
        }

        if defaults:
            self.load_conf(defaults)

        if confpath:
            self.load_conffile(confpath)

    @property
    def meowlflow(self):
        return self.settings["meowlflow"]

    @property
    def sentry(self):
        return self.settings["sentry"]

    def reload(self, confpath, inplace=False):
        if inplace:
            instance = self
            instance.load_conffile(confpath)
        else:
            instance = MeowlflowConfig(defaults=self.settings, confpath=confpath)
        return instance

    def load_conf(self, conf):
        for key, val in conf.items():
            self.settings[key].update(val)

    def load_conffile(self, confpath):
        with open(confpath, "r", encoding="utf-8") as conffile:
            self.load_conf(yaml.safe_load(conffile.read()))


GCONFIG = MeowlflowConfig(confpath=MEOWLFLOW_CONF_FILE)
