import typing

from smart_tv_telegram import Config
from smart_tv_telegram.devices import DeviceFinder


class DeviceFinderCollection:
    _finders: typing.List[DeviceFinder]

    def __init__(self):
        self._finders = list()

    def register_finder(self, finder: DeviceFinder):
        self._finders.append(finder)

    def get_finders(self, config: Config) -> typing.List[DeviceFinder]:
        return [finder for finder in self._finders if finder.is_enabled(config)]
