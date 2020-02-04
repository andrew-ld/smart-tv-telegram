import typing
import re
import functools
import time

from pyrogram.api.functions.messages import GetMessages
from pyrogram.api.functions.upload import GetFile
from pyrogram.api.types.message import Message
from pyrogram.api.types import InputDocumentFileLocation, InputMessageID
from pyrogram.errors.exceptions.flood_420 import FloodWait


if typing.TYPE_CHECKING:
    from . import BareServer


class Tools:
    RANGE_REGEX = re.compile(r"bytes=([0-9]+)-")
    BLOCK_SIZE = 1024 * 1024

    def iter_download(self: 'BareServer', message: Message, offset: int):
        session = self.client.media_sessions.get(
            message.media.document.dc_id
        )

        while True:

            try:

                part = session.send(
                    GetFile(
                        offset=offset,
                        limit=self.BLOCK_SIZE,
                        location=InputDocumentFileLocation(
                            id=message.media.document.id,
                            access_hash=message.media.document.access_hash,
                            file_reference=b"",  # bot can use empty fr
                            thumb_size=""
                        ),
                    )
                ).bytes

            # server is overloaded
            except FloodWait:
                time.sleep(0.2)
                continue

            return part, offset + len(part)

    @functools.lru_cache()
    def get_message(self: 'BareServer', mid: int) -> Message:
        res = self.client.send(
            GetMessages(
                id=[InputMessageID(id=mid)]
            )
        )

        if not res.messages:
            return False

        return res.messages[0]

    def parse_http_range(self, header: str):
        matches = self.RANGE_REGEX.search(header)

        if matches is None:
            return True, 400

        offset = matches.group(1)

        if not offset.isdigit():
            return True, 400

        offset = int(offset)
        safe_offset = (offset // self.BLOCK_SIZE) * self.BLOCK_SIZE
        data_to_skip = offset - safe_offset

        return False, safe_offset, data_to_skip
