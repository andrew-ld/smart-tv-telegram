import typing

from .device import Device, DeviceFinder, ROUTERS_RET_TYPE
from .upnp_device import UpnpDevice, UpnpDeviceFinder
from .chromecast_device import ChromecastDevice, ChromecastDeviceFinder
from .vlc_device import VlcDeviceFinder, VlcDevice
from .xbmc_device import XbmcDevice, XbmcDeviceFinder


FINDERS: typing.List[typing.Type[DeviceFinder]] = [
    UpnpDeviceFinder,
    ChromecastDeviceFinder,
    XbmcDeviceFinder,
    VlcDeviceFinder
]


__all__ = [
    "Device",
    "DeviceFinder",
    "UpnpDevice",
    "UpnpDeviceFinder",
    "ChromecastDevice",
    "ChromecastDeviceFinder",
    "XbmcDevice",
    "XbmcDeviceFinder",
    "VlcDevice",
    "VlcDeviceFinder",
    "FINDERS",
    "ROUTERS_RET_TYPE"
]
