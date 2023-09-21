import asyncio
import functools
import logging
import os
import pickle
import typing

import pyrogram

from async_lru import alru_cache
from pyrogram.handlers.handler import Handler
from pyrogram.raw.functions.auth import ExportAuthorization, ImportAuthorization
from pyrogram.raw.functions.help import GetConfig
from pyrogram.raw.functions.messages import GetMessages
from pyrogram.raw.functions.upload import GetFile
from pyrogram.raw.types import InputMessageID, Message, InputDocumentFileLocation
from pyrogram.errors import FloodWait
import pyrogram.session
from pyrogram.raw.types.upload import File

from . import Config

__all__ = [
    "Mtproto"
]


class Mtproto:
    _config: Config
    _client: pyrogram.Client

    def __init__(self, config: Config):
        self._config = config
        self._client = pyrogram.Client(config.session_name, config.api_id, config.api_hash,
                                       bot_token=config.token, sleep_threshold=0, workdir=os.getcwd())

    def register(self, handler: Handler):
        self._client.add_handler(handler)

    async def reply_message(self, message_id: int, chat_id: int, text: str):
        await self._client.send_message(
            chat_id,
            text=text,
            parse_mode="html",
            reply_to_message_id=message_id
        )

    @alru_cache()
    async def get_message(self, message_id: int) -> Message:
        messages = await self._client.invoke(GetMessages(id=[InputMessageID(id=message_id)]))

        if not messages.messages:
            raise ValueError("wrong message_id")

        message = messages.messages[0]

        if not isinstance(message, Message):
            raise ValueError(f"expected `Message`, found: `{type(message).__name__}`")

        return message

    async def health_check(self):
        if not all(x.is_connected.is_set() for x in self._client.media_sessions.values()):
            logging.log(logging.ERROR, "media session not connected")
            raise ConnectionError()

        if not self._client.session.is_connected.is_set():
            logging.log(logging.ERROR, "main session not connected")
            raise ConnectionError()

    async def get_block(self, message: Message, offset: int, block_size: int) -> bytes:
        session = self._client.media_sessions.get(message.media.document.dc_id)

        request = GetFile(
            offset=offset,
            limit=block_size,
            location=InputDocumentFileLocation(
                id=message.media.document.id,
                access_hash=message.media.document.access_hash,
                file_reference=b"",
                thumb_size=""
            )
        )

        result: typing.Optional[File] = None

        while not isinstance(result, File):
            try:
                result = await session.invoke(request, sleep_threshold=0)
            except FloodWait:  # file floodwait is fake
                await asyncio.sleep(self._config.file_fake_fw_wait)

        return result.bytes

    async def start(self):
        await self._client.start()

        config = await self._client.invoke(GetConfig())
        dc_ids = [x.id for x in config.dc_options]
        keys_path = self._config.session_name + ".keys"

        if os.path.exists(keys_path):
            keys = pickle.load(open(keys_path, "rb"))
        else:
            keys = {}

        for dc_id in dc_ids:
            session = functools.partial(pyrogram.session.Session, self._client, dc_id, is_media=True, test_mode=False)

            if dc_id != await self._client.storage.dc_id():
                if dc_id not in keys:
                    exported_auth = await self._client.invoke(ExportAuthorization(dc_id=dc_id))

                    auth = pyrogram.session.Auth(self._client, dc_id, False)
                    auth_key = await auth.create()

                    session = session(auth_key)
                    await session.start()

                    await session.invoke(ImportAuthorization(id=exported_auth.id, bytes=exported_auth.bytes))
                    keys[dc_id] = session.auth_key

                else:
                    session = session(keys[dc_id])
                    await session.start()

            else:
                session = session(await self._client.storage.auth_key())
                await session.start()

            self._client.media_sessions[dc_id] = session

        pickle.dump(keys, open(keys_path, "wb"))
