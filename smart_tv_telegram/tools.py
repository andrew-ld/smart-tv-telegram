import asyncio
import concurrent.futures
import re
import typing

from pyrogram.api.types import Message, MessageMediaDocument, Document, DocumentAttributeFilename

from smart_tv_telegram import Config


range_regex = re.compile(r"bytes=([0-9]+)-([0-9]+)?")
named_media_types = ["document", "video", "audio", "video_note", "animation"]

_executor = concurrent.futures.ThreadPoolExecutor()
_loop = asyncio.get_event_loop()


def mtproto_filename(message: Message) -> str:
    if not (
        isinstance(message.media, MessageMediaDocument) and
        isinstance(message.media.document, Document)
    ):
        raise TypeError()

    try:
        return next(
            attr.file_name
            for attr in message.media.document.attributes
            if isinstance(attr, DocumentAttributeFilename)
        )
    except StopIteration:
        raise TypeError()


def build_uri(config: Config, msg_id: int) -> str:
    return f"http://{config.listen_host}:{config.listen_port}/stream/{msg_id}"


def ascii_only(haystack: str) -> str:
    return "".join(c for c in haystack if ord(c) < 128)


def run_method_in_executor(func):
    async def wraps(*args):
        return await _loop.run_in_executor(_executor, func, *args)
    return wraps


def parse_http_range(http_range: str, block_size: int) -> typing.Tuple[int, int, typing.Optional[int]]:
    matches = range_regex.search(http_range)

    if matches is None:
        raise ValueError()

    offset = matches.group(1)

    if not offset.isdigit():
        raise ValueError()

    max_size = matches.group(2)

    if max_size and max_size.isdigit():
        max_size = int(max_size)
    else:
        max_size = None

    offset = int(offset)
    safe_offset = (offset // block_size) * block_size
    data_to_skip = offset - safe_offset

    return safe_offset, data_to_skip, max_size
