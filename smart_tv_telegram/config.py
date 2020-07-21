import ast
import configparser
import typing


__all__ = [
    "Config"
]


class Config:
    _api_id: int
    _api_hash: str
    _token: str
    _session_name: str
    _file_fake_fw_wait: float

    _device_request_timeout: int

    _listen_host: str
    _listen_port: int

    _upnp_enabled: bool
    _upnp_scan_timeout: int = 0

    _chromecast_enabled: bool
    _chromecast_scan_timeout: int = 0

    _xbmc_enabled: bool
    _xbmc_devices: typing.List[dict]

    _vlc_enabled: bool
    _vlc_devices: typing.List[dict]

    _admins: typing.List[int]
    _block_size: int

    def __init__(self, path: str):
        config = configparser.ConfigParser()
        config.read(path)

        self._api_id = int(config["mtproto"]["api_id"])
        self._api_hash = str(config["mtproto"]["api_hash"])
        self._token = str(config["mtproto"]["token"])
        self._session_name = str(config["mtproto"]["session_name"])
        self._file_fake_fw_wait = float(config["mtproto"]["file_fake_fw_wait"])

        self._listen_port = int(config["http"]["listen_port"])
        self._listen_host = str(config["http"]["listen_host"])

        self._upnp_enabled = bool(int(config["discovery"]["upnp_enabled"]))

        if self._upnp_enabled:
            self._upnp_scan_timeout = int(config["discovery"]["upnp_scan_timeout"])

        self._chromecast_enabled = bool(int(config["discovery"]["chromecast_enabled"]))

        self._device_request_timeout = int(config["discovery"]["device_request_timeout"])

        self._xbmc_enabled = bool(int(config["discovery"]["xbmc_enabled"]))

        if self._xbmc_enabled:
            self._xbmc_devices = ast.literal_eval(config["discovery"]["xbmc_devices"])

            if not isinstance(self._xbmc_devices, list):
                raise ValueError("xbmc_devices should be a list")

            if not all(isinstance(x, dict) for x in self._xbmc_devices):
                raise ValueError("xbmc_devices should contain only dict")

        else:
            self._xbmc_devices = []

        self._vlc_enabled = bool(int(config["discovery"]["vlc_enabled"]))

        if self._vlc_enabled:
            self._vlc_devices = ast.literal_eval(config["discovery"]["vlc_devices"])

            if not isinstance(self._xbmc_devices, list):
                raise ValueError("vlc_devices should be a list")

            if not all(isinstance(x, dict) for x in self._xbmc_devices):
                raise ValueError("vlc_devices should contain only dict")

        else:
            self._vlc_devices = []

        if self._chromecast_enabled:
            self._chromecast_scan_timeout = int(config["discovery"]["chromecast_scan_timeout"])

        self._admins = ast.literal_eval(config["bot"]["admins"])
        self._block_size = int(config["bot"]["block_size"])

        if not isinstance(self._admins, list):
            raise ValueError("admins should be a list")

        if not all(isinstance(x, int) for x in self._admins):
            raise ValueError("admins list should contain only integers")

    @property
    def file_fake_fw_wait(self) -> float:
        return self._file_fake_fw_wait

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
    def session_name(self) -> str:
        return self._session_name

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
    def xbmc_enabled(self) -> bool:
        return self._xbmc_enabled

    @property
    def xbmc_devices(self) -> typing.List[dict]:
        return self._xbmc_devices

    @property
    def vlc_enabled(self) -> bool:
        return self._vlc_enabled

    @property
    def vlc_devices(self) -> typing.List[dict]:
        return self._vlc_devices

    @property
    def admins(self) -> typing.List[int]:
        return self._admins

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def device_request_timeout(self) -> int:
        return self._device_request_timeout
