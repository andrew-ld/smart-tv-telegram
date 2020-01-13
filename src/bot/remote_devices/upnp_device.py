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

    def play(self, url: str):
        self._device.set_current_media(url)
        self._device.play()


class UpnpDeviceFinder(DeviceFinder):
    def __new__(cls, timeout: int = None, hacky: bool = False) -> typing.List[Device]:
        devices = upnp.discover('', '', timeout, upnp.URN_AVTransport_Fmt, 1)

        if not devices and hacky:
            devices = upnp.discover('', '', timeout, upnp.SSDP_ALL, 1)

        return [UpnpDevice(device) for device in devices]
