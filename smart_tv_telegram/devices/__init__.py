import typing

from .device import Device, DeviceFinder, RoutersDefType, RequestHandler
from .upnp_device import UpnpDevice, UpnpDeviceFinder
from .chromecast_device import ChromecastDevice, ChromecastDeviceFinder
from .vlc_device import VlcDeviceFinder, VlcDevice
from .web_device import WebDeviceFinder, WebDevice
from .xbmc_device import XbmcDevice, XbmcDeviceFinder


FINDERS: typing.List[typing.Type[DeviceFinder]] = [
    UpnpDeviceFinder,
    ChromecastDeviceFinder,
    XbmcDeviceFinder,
    VlcDeviceFinder,
    WebDeviceFinder
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
    "RoutersDefType",
    "RequestHandler",
    "WebDeviceFinder",
    "WebDevice"
]
