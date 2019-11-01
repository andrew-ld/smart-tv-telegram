import typing
import re

from pyrogram.api.functions.messages import GetMessages
from pyrogram.api.functions.upload import GetFile
from pyrogram.api.types.message import Message
from pyrogram.api.types import InputDocumentFileLocation, InputMessageID

if typing.TYPE_CHECKING:
    from . import BareServer


RANGE_REGEX = re.compile(r"bytes=([0-9]+)-")
BLOCK_SIZE = 1024 * 1024


class Tools:
    def iter_download(self: 'BareServer', message: Message, offset: int):
        session = self.client.media_sessions.get(
            message.media.document.dc_id
        )

        part = session.send(
            GetFile(
                offset=offset,
                limit=BLOCK_SIZE,
                location=InputDocumentFileLocation(
                    id=message.media.document.id,
                    access_hash=message.media.document.access_hash,
                    file_reference=message.media.document.file_reference,
                    thumb_size=""
                ),
            )
        ).bytes

        return part, offset + len(part)

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
        matches = RANGE_REGEX.search(header)

        if matches is None:
            return True, 400

        offset = matches.group(1)

        if not offset.isdigit():
            return True, 400

        offset = int(offset)
        safe_offset = (offset // BLOCK_SIZE) * BLOCK_SIZE
        data_to_skip = offset - safe_offset

        return False, safe_offset, data_to_skip
