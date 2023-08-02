import asyncio
import concurrent.futures
import functools
import re
import secrets
import typing

from pyrogram.raw.types import MessageMediaDocument, Document, DocumentAttributeFilename
from pyrogram.raw.types import Message as TlMessage
from pyrogram.types import Message as BoxedMessage

from . import Config

__all__ = [
    "mtproto_filename",
    "build_uri",
    "ascii_only",
    "run_method_in_executor",
    "parse_http_range",
    "pyrogram_filename",
    "secret_token",
    "base_url",
    "serialize_token",
    "AsyncDebounce"
]

_NAMED_MEDIA_TYPES = ("document", "video", "audio", "video_note", "animation")
_RANGE_REGEX = re.compile(r"bytes=([0-9]+)-([0-9]+)?")
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)


async def _debounce_wrap(
        function: typing.Callable[..., typing.Coroutine],
        args: typing.Tuple[typing.Any],
        timeout: int,
):
    await asyncio.sleep(timeout)
    await function(*args)


def base_url(config: Config) -> str:
    return f"http://{config.listen_host}:{config.listen_port}"


class AsyncDebounce:
    _function: typing.Callable[..., typing.Coroutine]
    _timeout: int
    _task: typing.Optional[asyncio.Task] = None
    _args: typing.Optional[typing.Tuple[typing.Any]] = None

    def __init__(self, function: typing.Callable[..., typing.Coroutine], timeout: int):
        self._function = function
        self._timeout = timeout

    def _run(self) -> bool:
        if self._args is None:
            return False

        self._task = asyncio.get_event_loop().create_task(_debounce_wrap(self._function, self._args, self._timeout))
        return True

    def update_args(self, *args) -> bool:
        if self._task is not None and self._task.done():
            return False

        if self._task is not None:
            self._task.cancel()

        self._args = args
        return self._run()

    def reschedule(self):
        return self._run()


def secret_token(nbytes: int = 8) -> int:
    return int.from_bytes(secrets.token_bytes(nbytes=nbytes), "big")


def serialize_token(message_id: int, token: int) -> int:
    return (token << 64) ^ message_id


def pyrogram_filename(message: BoxedMessage) -> str:
    try:
        return next(
            getattr(message, t).file_name
            for t in _NAMED_MEDIA_TYPES
            if getattr(message, t) is not None
        )
    except StopIteration as error:
        raise TypeError() from error


def mtproto_filename(message: TlMessage) -> str:
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
    except StopIteration as error:
        raise TypeError() from error


def build_uri(config: Config, msg_id: int, token: int) -> str:
    return f"http://{config.listen_host}:{config.listen_port}/stream/{msg_id}/{token}"


def ascii_only(haystack: str) -> str:
    return "".join(c for c in haystack if ord(c) < 128)


async def run_method_in_executor(func, *args, **kwargs):
    partial_function = functools.partial(func, *args, **kwargs)
    return await asyncio.get_event_loop().run_in_executor(_EXECUTOR, partial_function)


def parse_http_range(http_range: str, block_size: int) -> typing.Tuple[int, int, typing.Optional[int]]:
    matches = _RANGE_REGEX.search(http_range)

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
