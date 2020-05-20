import typing
from ipaddress import IPv4Address
from xml.sax.saxutils import escape

import async_upnp_client
from async_upnp_client import UpnpFactory, UpnpError
from async_upnp_client.aiohttp import AiohttpRequester
from async_upnp_client.search import async_search

from . import Device, DeviceFinder
from .. import Config
from ..tools import ascii_only


avtransport = "urn:schemas-upnp-org:service:AVTransport:1"

ddl_meta = """
<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
    xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
    xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
    <item id="R:0/0/0" parentID="R:0/0" restricted="true">
        <dc:title>{title}</dc:title>
        <upnp:class>object.item.videoItem.movie</upnp:class>
        <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">
            SA_RINCON65031_
        </desc>
    </item>
</DIDL-Lite>
"""


class UpnpDevice(Device):
    _device: async_upnp_client.UpnpDevice
    _service: async_upnp_client.UpnpService

    # noinspection PyMissingConstructor
    def __init__(self, device: async_upnp_client.UpnpDevice):
        self._device = device
        self._service = self._device.service(avtransport)
        self.device_name = self._device.friendly_name

    async def stop(self):
        stop = self._service.action("Stop")

        try:
            await stop.async_call(InstanceID=0)
        except UpnpError as e:
            if str(e) != "Transition not available":
                raise e

    async def play(self, url: str, title: str):
        set_url = self._service.action("SetAVTransportURI")
        meta = ddl_meta.format(title=escape(ascii_only(title)))
        await set_url.async_call(InstanceID=0, CurrentURI=url, CurrentURIMetaData=meta)

        play = self._service.action("Play")
        await play.async_call(InstanceID=0, Speed="1")


class UpnpDeviceFinder(DeviceFinder):
    @staticmethod
    async def find(config: Config) -> typing.List[Device]:
        devices = []
        requester = AiohttpRequester()
        factory = UpnpFactory(requester)
        source_ip = IPv4Address("0.0.0.0")

        async def on_response(data: typing.Mapping[str, typing.Any]) -> None:
            devices.append(await factory.async_create_device(data.get("LOCATION")))

        await async_search(service_type=avtransport,
                           source_ip=source_ip,
                           timeout=config.upnp_scan_timeout,
                           async_callback=on_response)

        return [UpnpDevice(device) for device in devices]
