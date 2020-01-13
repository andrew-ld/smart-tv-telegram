import typing
import pychromecast

from . import Device, DeviceFinder


class ChromecastDevice(Device):
    _device: pychromecast.Chromecast

    # noinspection PyMissingConstructor
    def __init__(self, device: typing.Any):
        self._device = device
        self._device.wait()

        self.device_name = self._device.device.friendly_name

    def stop(self):
        pass

    def play(self, url: str):
        self._device.play_media(url, 'video/mp4')


class ChromecastDeviceFinder(DeviceFinder):
    def __new__(cls, timeout: int = None, hacky: bool = False) -> typing.List[Device]:
        return [
            ChromecastDevice(device)
            for device in pychromecast.get_chromecasts(timeout=timeout, tries=0)
        ]
