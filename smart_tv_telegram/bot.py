import abc
import functools
import typing
import enum
import html

import async_timeout
from pyrogram import Client, filters
from pyrogram.filters import create
from pyrogram.handlers import MessageHandler
from pyrogram.types import ReplyKeyboardRemove, Message, KeyboardButton, ReplyKeyboardMarkup

from . import Config, Mtproto, Http
from .devices import UpnpDeviceFinder, ChromecastDeviceFinder, VlcDeviceFinder, XbmcDeviceFinder, Device
from .tools import build_uri, pyrogram_filename, secret_token

__all__ = [
    "Bot"
]


_REMOVE_KEYBOARD = ReplyKeyboardRemove()
_CANCEL_BUTTON = "^Cancel"


class States(enum.Enum):
    NOTHING = enum.auto()
    SELECT = enum.auto()


class StateData(abc.ABC):
    @abc.abstractmethod
    def get_associated_state(self) -> States:
        raise NotImplementedError


class SelectStateData(StateData):
    msg_id: int
    filename: str
    devices: typing.List[Device]

    def get_associated_state(self) -> States:
        return States.SELECT

    def __init__(self, msg_id: int, filename: str, devices: typing.List[Device]):
        self.msg_id = msg_id
        self.filename = filename
        self.devices = devices


class TelegramStateMachine:
    _states: typing.Dict[int, typing.Tuple[States, typing.Union[bool, StateData]]]

    def __init__(self):
        self._states = {}

    def get_state(self, message: Message) -> typing.Tuple[States, typing.Union[bool, StateData]]:
        user_id = message.from_user.id

        if user_id in self._states:
            return self._states[user_id]

        return States.NOTHING, False

    def set_state(self, message: Message, state: States, data: typing.Union[bool, StateData]) -> bool:
        if isinstance(data, bool) or data.get_associated_state() == state:
            self._states[message.from_user.id] = (state, data)
            return True

        raise TypeError()


class Bot:
    _config: Config
    _state_machine: TelegramStateMachine
    _mtproto: Mtproto
    _http: Http

    def __init__(self, mtproto: Mtproto, config: Config, http: Http):
        self._config = config
        self._mtproto = mtproto
        self._http = http
        self._state_machine = TelegramStateMachine()

    def prepare(self):
        admin_filter = filters.chat(self._config.admins) & filters.private
        self._mtproto.register(MessageHandler(self._new_document, filters.document & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, filters.video & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, filters.audio & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, filters.animation & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, filters.voice & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, filters.video_note & admin_filter))

        state_filter = create(lambda _, __, m: self._state_machine.get_state(m)[0] == States.SELECT)
        self._mtproto.register(MessageHandler(self._select_device, filters.text & admin_filter & state_filter))

    async def _select_device(self, _: Client, message: Message):
        data: SelectStateData
        _, data = self._state_machine.get_state(message)

        self._state_machine.set_state(message, States.NOTHING, False)
        reply = functools.partial(message.reply, reply_markup=_REMOVE_KEYBOARD)

        if message.text == _CANCEL_BUTTON:
            await reply("Cancelled")
            return

        try:
            device = next(
                device
                for device in data.devices
                if repr(device) == message.text
            )
        except StopIteration:
            await reply("Wrong device")
            return

        async with async_timeout.timeout(self._config.device_request_timeout) as cm:
            token = secret_token()
            self._http.add_token(data.msg_id, token)
            uri = build_uri(self._config, data.msg_id, token)

            # noinspection PyBroadException
            try:
                await device.stop()
                await device.play(uri, data.filename)

            except Exception as ex:
                await reply(
                    "Error while communicate with the device:\n\n"
                    f"<code>{html.escape(str(ex))}</code>"
                )

            else:
                await reply(f"Playing ID: {data.msg_id}")

        if cm.expired:
            await reply(f"Timeout while communicate with the device")

    async def _new_document(self, _: Client, message: Message):
        devices = []

        if self._config.upnp_enabled:
            devices.extend(await UpnpDeviceFinder.find(self._config))

        if self._config.chromecast_enabled:
            # noinspection PyUnresolvedReferences
            devices.extend(await ChromecastDeviceFinder.find(self._config))

        if self._config.xbmc_enabled:
            devices.extend(await XbmcDeviceFinder.find(self._config))

        if self._config.vlc_enabled:
            devices.extend(await VlcDeviceFinder.find(self._config))

        if devices:
            try:
                filename = pyrogram_filename(message)
            except TypeError:
                filename = "NaN"

            self._state_machine.set_state(
                message,
                States.SELECT,
                SelectStateData(
                    message.message_id,
                    filename,
                    devices.copy()
                )
            )

            buttons = [[KeyboardButton(repr(device))] for device in devices]
            buttons.append([KeyboardButton(_CANCEL_BUTTON)])
            markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
            await message.reply("Select a device", reply_markup=markup)

        else:
            await message.reply("Supported devices not found in the network", reply_markup=_REMOVE_KEYBOARD)
