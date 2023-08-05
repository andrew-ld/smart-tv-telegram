import asyncio
import typing

import pychromecast
import zeroconf

from pychromecast.const import MESSAGE_TYPE
from pychromecast.controllers.media import MediaController, TYPE_PAUSE, TYPE_PLAY, TYPE_STOP

from . import Device, DeviceFinder, RoutersDefType, DevicePlayerFunction
from .. import Config
from ..tools import run_method_in_executor

__all__ = [
    "ChromecastDevice",
    "ChromecastDeviceFinder"
]


def _extract_sender(controller: MediaController) -> typing.Callable[[typing.Dict[str, str]], None]:
    return getattr(controller, "_send_command")


async def _send_command(controller: MediaController, command: str):
    await run_method_in_executor(_extract_sender(controller), {MESSAGE_TYPE: command})


class RefCountedPyChromecastBrowser:
    _ref_count: int
    obj: pychromecast.CastBrowser

    def __init__(self, default_ref_count: int, obj: pychromecast.CastBrowser):
        assert default_ref_count > 0
        self._ref_count = default_ref_count
        self.obj = obj

    def is_unreached(self):
        assert self._ref_count >= 0
        return self._ref_count == 0

    def defref(self):
        assert self._ref_count > 0
        self._ref_count -= 1


class ChromecastGenericDeviceFunction(DevicePlayerFunction):
    _command: str
    _device: pychromecast.Chromecast

    def __init__(self, command: str, device: pychromecast.Chromecast):
        self._command = command
        self._device = device

    async def get_name(self) -> str:
        return self._command

    async def handle(self):
        await _send_command(self._device.media_controller, self._command)

    async def is_enabled(self, config: Config):
        return True


class ChromecastDevice(Device):
    _device: pychromecast.Chromecast
    _broswer: RefCountedPyChromecastBrowser | None

    def __init__(self, device: pychromecast.Chromecast, broswer: RefCountedPyChromecastBrowser):
        self._device = device
        self._broswer = broswer

    def get_device_name(self) -> str:
        return self._device.name

    async def stop(self):
        pass

    async def on_close(self, local_token: int):
        self._device.disconnect(blocking=False)

    async def play(self, url: str, title: str, local_token: int):
        await run_method_in_executor(self._device.connect)
        await run_method_in_executor(self._device.wait)

        if not self._device.is_idle:
            await run_method_in_executor(self._device.quit_app)

            while self._device.status.app_id is not None:
                await asyncio.sleep(0.1)

        await run_method_in_executor(self._device.play_media, url, "video/mp4", title)

    def get_player_functions(self) -> typing.List[DevicePlayerFunction]:
        return [
            ChromecastGenericDeviceFunction(TYPE_PAUSE, self._device),
            ChromecastGenericDeviceFunction(TYPE_PLAY, self._device),
            ChromecastGenericDeviceFunction(TYPE_STOP, self._device),
        ]

    async def release(self):
        broswer = self._broswer
        self._broswer = None

        if broswer is None:
            return

        broswer.defref()

        if broswer.is_unreached():
            await run_method_in_executor(broswer.obj.stop_discovery)


class ChromecastDeviceFinder(DeviceFinder):
    zeroconf: zeroconf.Zeroconf

    def __init__(self):
        self._zero_conf = zeroconf.Zeroconf()

    async def find(self, config: Config) -> typing.List[Device]:
        devices, browser = await run_method_in_executor(
            pychromecast.get_chromecasts,
            timeout=config.chromecast_scan_timeout,
            blocking=True,
            zeroconf_instance=self._zero_conf
        )

        if not devices:
            await run_method_in_executor(browser.stop_discovery)
            return []

        ref_counted_broswer = RefCountedPyChromecastBrowser(len(devices), browser)

        return [ChromecastDevice(device, ref_counted_broswer) for device in devices]

    @staticmethod
    def is_enabled(config: Config) -> bool:
        return config.chromecast_enabled

    async def get_routers(self, config: Config) -> RoutersDefType:
        return []
