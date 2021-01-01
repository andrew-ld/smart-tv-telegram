from .config import Config
from .mtproto import Mtproto
from .http import Http, OnStreamClosed
from .bot import Bot


__version__ = "1.2.1"
__version_info__ = ("1", "2", "1")
__author__ = "https://github.com/andrew-ld"


__all__ = [
    "Config",
    "Mtproto",
    "Http",
    "OnStreamClosed",
    "Bot",
    "__version__",
    "__version_info__",
    "__author__",
]
