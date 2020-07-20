import abc
import typing
import enum
import html

import async_timeout
from pyrogram import Message, MessageHandler, Filters, ReplyKeyboardMarkup, KeyboardButton, Client, ReplyKeyboardRemove

from . import Config, Mtproto
from .devices import UpnpDeviceFinder, ChromecastDeviceFinder, VlcDeviceFinder, XbmcDeviceFinder, Device
from .tools import named_media_types, build_uri


REMOVE_KEYBOARD = ReplyKeyboardRemove()
CANCEL_BUTTON = "^Cancel"


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

    def __init__(self, mtproto: Mtproto, config: Config):
        self._config = config
        self._mtproto = mtproto
        self._state_machine = TelegramStateMachine()

    def prepare(self):
        admin_filter = Filters.chat(self._config.admins)
        self._mtproto.register(MessageHandler(self._new_document, Filters.document & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, Filters.video & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, Filters.audio & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, Filters.animation & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, Filters.voice & admin_filter))
        self._mtproto.register(MessageHandler(self._new_document, Filters.video_note & admin_filter))
        self._mtproto.register(MessageHandler(self._play, Filters.text & admin_filter))

    # noinspection PyUnusedLocal
    async def _play(self, client: Client, message: Message):
        state, data = self._state_machine.get_state(message)

        if state != States.SELECT:
            return

        data: SelectStateData

        self._state_machine.set_state(message, States.NOTHING, False)

        if message.text == CANCEL_BUTTON:
            await message.reply("Cancelled", reply_markup=REMOVE_KEYBOARD)
            return

        try:
            device = next(
                device
                for device in data.devices
                if repr(device) == message.text
            )
        except StopIteration:
            await message.reply("Wrong device", reply_markup=REMOVE_KEYBOARD)
            return

        async with async_timeout.timeout(self._config.device_request_timeout) as cm:
            uri = build_uri(self._config, data.msg_id)

            # noinspection PyBroadException
            try:
                await device.stop()
                await device.play(uri, data.filename)

            except Exception as ex:
                await message.reply(
                    "Error while communicate with the device:\n\n"
                    f"<code>{html.escape(str(ex))}</code>",
                    reply_markup=REMOVE_KEYBOARD
                )

            else:
                await message.reply(f"Playing ID: {data.msg_id}", reply_markup=REMOVE_KEYBOARD)

        if cm.expired:
            await message.reply(f"Timeout while communicate with the device", reply_markup=REMOVE_KEYBOARD)

    # noinspection PyUnusedLocal
    async def _new_document(self, client: Client, message: Message):
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
            file_name = ""

            for typ in named_media_types:
                obj = getattr(message, typ)

                if obj is not None:
                    file_name = obj.file_name
                    break

            self._state_machine.set_state(
                message,
                States.SELECT,
                SelectStateData(
                    message.message_id,
                    file_name,
                    devices.copy()
                )
            )

            buttons = [[KeyboardButton(repr(device))] for device in devices]
            buttons.append([KeyboardButton(CANCEL_BUTTON)])
            markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True)
            await message.reply("Select a device", reply_markup=markup)

        else:
            await message.reply("Supported devices not found in the network", reply_markup=REMOVE_KEYBOARD)
