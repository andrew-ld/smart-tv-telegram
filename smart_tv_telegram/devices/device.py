import abc
import typing

from aiohttp.web_request import Request
from aiohttp.web_response import Response

from .. import Config


RoutersDefType = typing.List[typing.Tuple[str, typing.Callable[[Request], typing.Awaitable[Response]]]]


__all__ = [
    "Device",
    "DeviceFinder",
    "RoutersDefType"
]


class Device(abc.ABC):
    # noinspection PyUnusedLocal
    @abc.abstractmethod
    def __init__(self, device: typing.Any):
        raise NotImplementedError

    @abc.abstractmethod
    async def stop(self):
        raise NotImplementedError

    @abc.abstractmethod
    async def play(self, url: str, title: str):
        raise NotImplementedError

    @abc.abstractmethod
    def get_device_name(self) -> str:
        raise NotImplementedError

    def __repr__(self):
        return self.get_device_name()


class DeviceFinder(abc.ABC):
    @staticmethod
    @abc.abstractmethod
    async def find(config: Config) -> typing.List[Device]:
        raise NotImplementedError

    @staticmethod
    @abc.abstractmethod
    def is_enabled(config: Config) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    async def get_routers(self, config: Config) -> RoutersDefType:
        raise NotImplementedError
