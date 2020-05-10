import os
import pickle
import pyrogram

from async_lru import alru_cache

from pyrogram.api.functions.auth import ExportAuthorization, ImportAuthorization
from pyrogram.api.functions.help import GetConfig
from pyrogram.api.functions.messages import GetMessages
from pyrogram.api.functions.upload import GetFile
from pyrogram.api.types import InputMessageID, Message, InputDocumentFileLocation
from pyrogram.client.handlers.handler import Handler
from pyrogram.session import Session

from . import Config


class MtprotoController:
    _config: Config
    _client: pyrogram.Client

    def __init__(self, config: Config):
        self._config = config
        self._client = pyrogram.Client(config.session_name, config.api_id, config.api_hash, bot_token=config.token)

    def register(self, handler: Handler):
        self._client.add_handler(handler)

    @alru_cache(cache_exceptions=False)
    async def get_message(self, message_id: int) -> Message:
        messages = await self._client.send(GetMessages(id=[InputMessageID(id=message_id)]))

        if not messages.messages:
            raise ValueError()

        return messages.messages[0]

    async def get_block(self, message: Message, offset: int, block_size: int) -> bytes:
        doc = message.media.document
        session = self._client.media_sessions.get(doc.dc_id)
        location = InputDocumentFileLocation(id=doc.id, access_hash=doc.access_hash, file_reference=b"", thumb_size="")
        result = await session.send(GetFile(offset=offset, limit=block_size, location=location))
        return result.bytes

    async def start(self):
        await self._client.start()

        config = await self._client.send(GetConfig())
        dc_ids = [x.id for x in config.dc_options]
        keys_path = self._config.session_name + ".keys"

        if os.path.exists(keys_path):
            keys = pickle.load(open(keys_path, "rb"))
        else:
            keys = {}

        for dc_id in dc_ids:
            if dc_id != self._client.storage.dc_id():
                if dc_id not in keys:
                    exported_auth = await self._client.send(ExportAuthorization(dc_id=dc_id))

                    auth = pyrogram.session.Auth(self._client, dc_id)
                    auth_key = await auth.create()

                    session = Session(self._client, dc_id, auth_key, is_media=True)
                    await session.start()

                    await session.send(ImportAuthorization(id=exported_auth.id, bytes=exported_auth.bytes))
                    keys[dc_id] = session.auth_key

                else:
                    session = pyrogram.session.Session(self._client, dc_id, keys[dc_id], is_media=True)
                    await session.start()

            else:
                session = pyrogram.session.Session(self._client, dc_id, self._client.storage.auth_key(), is_media=True)
                await session.start()

            self._client.media_sessions[dc_id] = session

        pickle.dump(keys, open(keys_path, "wb"))
