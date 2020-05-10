import abc
import typing


class Device(abc.ABC):
    device_name: str

    # noinspection PyUnusedLocal
    @abc.abstractmethod
    def __init__(self, device: typing.Any):
        raise NotImplementedError

    @abc.abstractmethod
    def stop(self):
        raise NotImplementedError

    @abc.abstractmethod
    def play(self, url: str, title: str):
        raise NotImplementedError

    def __repr__(self):
        return self.device_name


class DeviceFinder(abc.ABC):
    @staticmethod
    def find(timeout: int = None) -> typing.List[Device]:
        raise NotImplementedError
