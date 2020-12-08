import functools
import typing

from aiohttp.web_request import Request
from aiohttp.web_response import Response

from smart_tv_telegram import Config
from smart_tv_telegram.devices import DeviceFinder, RoutersDefType, Device, RequestHandler
from smart_tv_telegram.tools import secret_token, AsyncDebounce


__all__ = [
    "WebDeviceFinder",
    "WebDevice"
]


class WebDevice(Device):
    _url_to_play: typing.Optional[str] = None
    _device_name: str
    _token: int

    def __init__(self, device_name: str, token: int):
        self._device_name = device_name
        self._token = token

    async def stop(self):
        self._url_to_play = None

    async def play(self, url: str, title: str):
        self._url_to_play = url

    def get_token(self) -> int:
        return self._token

    def get_device_name(self) -> str:
        return self._device_name

    def get_url_to_play(self) -> typing.Optional[str]:
        tmp = self._url_to_play
        self._url_to_play = None
        return tmp


class WebDeviceApiRequestRegisterDevice(RequestHandler):
    _config: Config
    _devices: typing.Dict[WebDevice, AsyncDebounce]

    def __init__(self, config: Config, devices: typing.Dict[WebDevice, AsyncDebounce]):
        self._config = config
        self._devices = devices

    def get_path(self) -> str:
        return "/web/api/register/{password}"

    async def _remove_device(self, device: WebDevice):
        try:
            del self._devices[device]
        except KeyError:
            pass

    async def handle(self, request: Request) -> Response:
        password = request.match_info["password"]

        if password != self._config.web_ui_password:
            return Response(status=403)

        token = secret_token()
        device = WebDevice(f"web @({request.remote})", token)

        remove = functools.partial(self._remove_device, device)
        self._devices[device] = debounce = AsyncDebounce(remove, self._config.request_gone_timeout)
        debounce.update_args()

        return Response(status=200, body=str(token))


class WebDeviceApiRequestPoll(RequestHandler):
    _config: Config
    _devices: typing.Dict[WebDevice, AsyncDebounce]

    def __init__(self, config: Config, devices: typing.Dict[WebDevice, AsyncDebounce]):
        self._devices = devices
        self._config = config

    def get_path(self) -> str:
        return "/web/api/poll/{token}"

    async def handle(self, request: Request) -> Response:
        try:
            token = int(request.match_info["token"])
        except ValueError:
            return Response(status=400)

        try:
            device = next(
                d
                for d in self._devices.keys()
                if d.get_token() == token
            )
        except StopIteration:
            return Response(status=404)

        self._devices[device].update_args()
        url_to_play = device.get_url_to_play()

        if url_to_play is None:
            return Response(status=302)

        return Response(status=200, body=url_to_play)


class WebDeviceFinder(DeviceFinder):
    _devices: typing.Dict[WebDevice, AsyncDebounce]

    def __init__(self):
        self._devices = dict()

    async def find(self, config: Config) -> typing.List[Device]:
        return list(self._devices.keys())

    @staticmethod
    def is_enabled(config: Config) -> bool:
        return config.web_ui_enabled

    async def get_routers(self, config: Config) -> RoutersDefType:
        return [
            WebDeviceApiRequestRegisterDevice(config, self._devices),
            WebDeviceApiRequestPoll(config, self._devices)
        ]
