import typing

import catt.api

from . import Device, DeviceFinder, RoutersDefType, DevicePlayerFunction
from .. import Config
from ..tools import run_method_in_executor

__all__ = [
    "ChromecastDevice",
    "ChromecastDeviceFinder"
]


class ChromecastPlayFunction(DevicePlayerFunction):
    _device: catt.api.CattDevice

    def __init__(self, device: catt.api.CattDevice):
        self._device = device

    async def get_name(self) -> str:
        return "PLAY"

    async def handle(self):
        await run_method_in_executor(self._device.play)

    async def is_enabled(self, config: Config):
        return True


class ChromecastPauseFunction(DevicePlayerFunction):
    _device: catt.api.CattDevice

    def __init__(self, device: catt.api.CattDevice):
        self._device = device

    async def get_name(self) -> str:
        return "PAUSE"

    async def handle(self):
        await run_method_in_executor(self._device.pause)

    async def is_enabled(self, config: Config):
        return True


class ChromecastDevice(Device):
    _device: catt.api.CattDevice

    def __init__(self, device: catt.api.CattDevice):
        self._device = device

    def get_device_name(self) -> str:
        return self._device.name

    async def stop(self):
        pass

    async def on_close(self, local_token: int):
        await run_method_in_executor(self._device.stop)

    async def play(self, url: str, title: str, local_token: int):
        await run_method_in_executor(self._device.play_url, url, title=title)

    def get_player_functions(self) -> typing.List[DevicePlayerFunction]:
        return [
            ChromecastPlayFunction(self._device),
            ChromecastPauseFunction(self._device)
        ]


class ChromecastDeviceFinder(DeviceFinder):
    _devices_cache: typing.Dict[str, catt.api.CattDevice]

    def __init__(self):
        self._devices_cache = {}

    async def find(self, config: Config) -> typing.List[Device]:
        found_devices: typing.List[catt.api.CattDevice] = await run_method_in_executor(catt.api.discover)
        cached_devices: typing.List[catt.api.CattDevice] = []

        for found_device in found_devices:
            cached_devices.append(self._devices_cache.setdefault(found_device.ip_addr, found_device))

        return [ChromecastDevice(device) for device in cached_devices]

    @staticmethod
    def is_enabled(config: Config) -> bool:
        return config.chromecast_enabled

    async def get_routers(self, config: Config) -> RoutersDefType:
        return []
