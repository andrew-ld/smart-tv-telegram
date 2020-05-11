import asyncio
import concurrent.futures
import functools
import typing

from pyrogram import Message, MessageHandler, Filters, ReplyKeyboardMarkup, KeyboardButton, Client, ReplyKeyboardRemove

from smart_tv_telegram import Config, MtprotoController
from smart_tv_telegram.devices import UpnpDeviceFinder, ChromecastDeviceFinder
from smart_tv_telegram.tools import named_media_types


class BotController:
    _config: Config
    _mtproto: MtprotoController
    _states: typing.Dict[int, typing.Tuple[str, typing.Any]]
    _pool: concurrent.futures.ThreadPoolExecutor
    _loop: asyncio.AbstractEventLoop

    def __init__(self, mtproto: MtprotoController, config: Config):
        self._config = config
        self._mtproto = mtproto
        self._states = {}
        self._loop = asyncio.get_event_loop()
        self._pool = concurrent.futures.ThreadPoolExecutor()

    def _get_state(self, message: Message) -> typing.Tuple[typing.Union[bool, str], typing.Tuple[typing.Any]]:
        user_id = message.from_user.id

        if user_id in self._states:
            return self._states[user_id][0], self._states[user_id][1:]

        return False, tuple()

    def _set_state(self, message: Message, state: typing.Union[str, bool], *data: typing.Any):
        self._states[message.from_user.id] = (state, *data)

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
        state, args = self._get_state(message)

        if state != "select":
            return

        self._set_state(message, False)

        if message.text == "Cancel":
            await message.reply("Cancelled")
            return

        # noinspection PyTupleAssignmentBalance
        msg_id, filename, devices = args

        try:
            device = next(
                device
                for device in devices
                if repr(device) == message.text
            )
        except StopIteration:
            await message.reply("Wrong device")
            return

        url = f"http://{self._config.listen_host}:{self._config.listen_port}/stream/{msg_id}"
        play = functools.partial(device.play, url, filename)
        await self._loop.run_in_executor(self._pool, play)

        await message.reply(f"Playing ID: {msg_id}", reply_markup=ReplyKeyboardRemove())

    # noinspection PyUnusedLocal
    async def _new_document(self, client: Client, message: Message):
        devices = []

        if self._config.upnp_enabled:
            finder = functools.partial(UpnpDeviceFinder.find, self._config.upnp_scan_timeout)
            devices.extend(await self._loop.run_in_executor(self._pool, finder))

        if self._config.chromecast_enabled:
            finder = functools.partial(ChromecastDeviceFinder.find, self._config.chromecast_scan_timeout)
            devices.extend(await self._loop.run_in_executor(self._pool, finder))

        if devices:
            file_name = ""

            for typ in named_media_types:
                obj = getattr(message, typ)

                if obj is not None:
                    file_name = obj.file_name
                    break

            self._set_state(message, "select", message.message_id, file_name, devices.copy())

            buttons = [[KeyboardButton(repr(device))] for device in devices]
            buttons.append([KeyboardButton("Cancel")])
            markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True)

            await message.reply("Select a device", reply_markup=markup)

        else:
            await message.reply("Supported devices not found in the network")
