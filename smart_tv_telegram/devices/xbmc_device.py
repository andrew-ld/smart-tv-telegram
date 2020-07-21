# from: https://github.com/home-assistant/core/blob/dev/homeassistant/components/kodi/media_player.py

import asyncio
import json
import logging
import uuid
import aiohttp
import typing

from .. import Config
from . import Device, DeviceFinder


__all__ = [
    "XbmcDevice",
    "XbmcDeviceFinder"
]


_LOGGER = logging.getLogger(__name__)
_ARG_TYPE = typing.Union[typing.AnyStr, int, bool]

_JSON_HEADERS = {"content-type": "application/json"}
_JSONRPC_VERSION = "2.0"

_ATTR_JSONRPC = "jsonrpc"
_ATTR_METHOD = "method"
_ATTR_PARAMS = "params"
_ATTR_ID = "id"


class XbmcDeviceParams:
    _host: str
    _port: int
    _username: typing.Optional[str] = None
    _password: typing.Optional[str] = None

    def __init__(self, params: typing.Dict[str, typing.AnyStr]):
        self._host = params["host"]
        self._port = params["port"]

        if "username" in params:
            self._username = params["username"]
            self._password = params["password"]

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    @property
    def username(self) -> typing.Optional[str]:
        return self._username

    @property
    def password(self) -> typing.Optional[str]:
        return self._password


class XbmcDevice(Device):
    _auth: typing.Optional[aiohttp.BasicAuth]
    _http_url: str
    _host: str

    # noinspection PyMissingConstructor
    def __init__(self, device: XbmcDeviceParams):
        if device.username:
            self._auth = aiohttp.BasicAuth(device.username, device.password)
        else:
            self._auth = None

        self._http_url = f"http://{device.host}:{device.port}/jsonrpc"
        self._host = device.host

    def get_device_name(self) -> str:
        return f"xbmc @{self._host}"

    async def _call(self, method: str, **args: typing.Union[_ARG_TYPE, typing.Mapping[str, _ARG_TYPE]]):
        data = {
            _ATTR_JSONRPC: _JSONRPC_VERSION,
            _ATTR_METHOD: method,
            _ATTR_ID: str(uuid.uuid4()),
            _ATTR_PARAMS: args
        }

        response = None
        session = aiohttp.ClientSession(auth=self._auth, headers=_JSON_HEADERS)

        try:
            response = await session.post(self._http_url, data=json.dumps(data))

            if response.status == 401:
                _LOGGER.error(
                    "Error fetching Kodi data. HTTP %d Unauthorized. "
                    "Password is incorrect.", response.status)
                return None

            if response.status != 200:
                _LOGGER.error(
                    "Error fetching Kodi data. HTTP %d", response.status)
                return None

            response_json = await response.json()

            if "error" in response_json:
                _LOGGER.error(
                    "RPC Error Code %d: %s",
                    response_json["error"]["code"],
                    response_json["error"]["message"])
                return None

            return response_json["result"]

        except (aiohttp.ClientError,
                asyncio.TimeoutError,
                ConnectionRefusedError):
            return None

        finally:
            if response:
                response.close()

            await session.close()

    async def stop(self):
        players = await self._call("Player.GetActivePlayers")

        if players:
            await self._call("Player.Stop", playerid=players[0]["playerid"])

    async def play(self, url: str, title: str):
        await self._call("Playlist.Clear", playlistid=0)
        await self._call("Playlist.Add", playlistid=0, item={"file": url})
        await self._call("Player.Open", item={"playlistid": 0}, options={"repeat": "one"})


class XbmcDeviceFinder(DeviceFinder):
    @staticmethod
    async def find(config: Config) -> typing.List[Device]:
        return [
            XbmcDevice(XbmcDeviceParams(params))
            for params in config.xbmc_devices
        ]
