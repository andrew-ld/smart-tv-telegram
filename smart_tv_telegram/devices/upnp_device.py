import typing

from . import upnp
from . import Device, DeviceFinder


class UpnpDevice(Device):
    _device: upnp.DlnapDevice

    # noinspection PyMissingConstructor
    def __init__(self, device: typing.Any):
        self._device = device
        self.device_name = repr(self._device)

    def stop(self):
        self._device.stop()

    def play(self, url: str, title: str):
        self._device.set_current_media(url, title)
        self._device.play()


class UpnpDeviceFinder(DeviceFinder):
    @staticmethod
    def find(timeout: int = None) -> typing.List[Device]:
        return [
            UpnpDevice(device)
            for device in upnp.discover("", "", timeout, upnp.URN_AVTransport_Fmt, 1)
        ]
