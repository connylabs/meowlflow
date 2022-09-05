# -*- coding: utf-8 -*-
from importlib.metadata import version, PackageNotFoundError


__version__ = "0.0.0"
try:
    __version__ = version("meowlflow")
except PackageNotFoundError:
    # package is not installed
    pass
