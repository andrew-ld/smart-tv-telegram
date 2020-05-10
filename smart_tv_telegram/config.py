import ast
import configparser

import typing


class Config:
    _api_id: int
    _api_hash: str
    _token: str

    _listen_host: str
    _listen_port: int

    _upnp_enabled: bool
    _upnp_scan_timeout: int = 0

    _chromecast_enabled: bool
    _chromecast_scan_timeout: int = 0

    _admins: typing.List[int]
    _block_size: int

    def __init__(self, path: str):
        config = configparser.ConfigParser()
        config.read(path)

        self._api_id = int(config["mtproto"]["api_id"])
        self._api_hash = str(config["mtproto"]["api_hash"])
        self._token = str(config["mtproto"]["token"])

        self._listen_port = int(config["http"]["listen_port"])
        self._listen_host = str(config["http"]["listen_host"])

        self._upnp_enabled = bool(config["discovery"]["upnp_enabled"])

        if self._upnp_enabled:
            self._upnp_scan_timeout = int(config["discovery"]["upnp_scan_timeout"])

        self._chromecast_enabled = bool(config["discovery"]["chromecast_enabled"])

        if self._chromecast_enabled:
            self._chromecast_scan_timeout = int(config["discovery"]["chromecast_scan_timeout"])

        self._admins = ast.literal_eval(config["bot"]["admins"])
        self._block_size = int(config["bot"]["block_size"])

        if not isinstance(self._admins, list):
            raise ValueError("admins should be a list")

        if not all(isinstance(x, int) for x in self._admins):
            raise ValueError("admins list should contain only integers")

    @property
    def api_id(self) -> int:
        return self._api_id

    @property
    def api_hash(self) -> str:
        return self._api_hash

    @property
    def token(self) -> str:
        return self._token

    @property
    def listen_host(self) -> str:
        return self._listen_host

    @property
    def listen_port(self) -> int:
        return self._listen_port

    @property
    def upnp_enabled(self) -> bool:
        return self._upnp_enabled

    @property
    def upnp_scan_timeout(self) -> int:
        return self._upnp_scan_timeout

    @property
    def chromecast_enabled(self) -> bool:
        return self._chromecast_enabled

    @property
    def chromecast_scan_timeout(self) -> int:
        return self._chromecast_scan_timeout

    @property
    def admins(self) -> typing.List[int]:
        return self._admins

    @property
    def block_size(self) -> int:
        return self._block_size
