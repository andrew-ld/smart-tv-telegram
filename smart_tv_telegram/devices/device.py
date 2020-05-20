import abc
import typing

from smart_tv_telegram import Config


class Device(abc.ABC):
    device_name: str

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

    def __repr__(self):
        return self.device_name


class DeviceFinder(abc.ABC):
    @staticmethod
    async def find(config: Config) -> typing.List[Device]:
        raise NotImplementedError
