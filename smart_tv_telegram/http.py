import abc
import asyncio
import os.path
import typing
from urllib.parse import quote

from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from pyrogram.raw.types import MessageMediaDocument, Document
from pyrogram.utils import get_peer_id

from . import Config, Mtproto, DeviceFinderCollection
from .tools import parse_http_range, mtproto_filename, serialize_token, AsyncDebounce

__all__ = [
    "Http",
    "OnStreamClosed"
]


class OnStreamClosed(abc.ABC):
    @abc.abstractmethod
    async def handle(self, remains: float, chat_id: int, message_id: int, local_token: int):
        raise NotImplementedError


class Http:
    _mtproto: Mtproto
    _config: Config
    _finders: DeviceFinderCollection
    _on_stream_closed: typing.Optional[OnStreamClosed] = None

    _tokens: typing.Set[int]
    _downloaded_blocks: typing.Dict[int, typing.Set[int]]
    _stream_debounce: typing.Dict[int, AsyncDebounce]
    _stream_transports: typing.Dict[int, typing.Set[asyncio.Transport]]

    def __init__(self, mtproto: Mtproto, config: Config, finders: DeviceFinderCollection):
        self._mtproto = mtproto
        self._config = config
        self._finders = finders

        self._tokens = set()
        self._downloaded_blocks = {}
        self._stream_debounce = {}
        self._stream_transports = {}

    def set_on_stream_closed_handler(self, handler: OnStreamClosed):
        self._on_stream_closed = handler

    async def start(self):
        app = web.Application()
        app.router.add_static("/static/", os.path.dirname(__file__) + "/static/")
        app.router.add_get("/stream/{message_id}/{token}", self._stream_handler)
        app.router.add_options("/stream/{message_id}/{token}", self._upnp_discovery_handler)
        app.router.add_put("/stream/{message_id}/{token}", self._upnp_discovery_handler)
        app.router.add_get("/healthcheck", self._health_check_handler)

        for finder in self._finders.get_finders(self._config):
            routers = await finder.get_routers(self._config)

            for handler in routers:
                app.router.add_route(handler.get_method(), handler.get_path(), handler.handle)

        # noinspection PyProtectedMember
        await web._run_app(app, host=self._config.listen_host, port=self._config.listen_port)

    def add_remote_token(self, message_id: int, partial_remote_token: int) -> int:
        local_token = serialize_token(message_id, partial_remote_token)
        self._tokens.add(local_token)
        return local_token

    def _check_local_token(self, local_token: int) -> bool:
        return local_token in self._tokens

    @staticmethod
    def _write_http_range_headers(result: StreamResponse, read_after: int,  size: int, max_size: int):
        result.headers.setdefault("Content-Range", f"bytes {read_after}-{max_size}/{size}")
        result.headers.setdefault("Accept-Ranges", "bytes")
        result.headers.setdefault("Content-Length", str(size))

    @staticmethod
    def _write_access_control_headers(result: StreamResponse):
        result.headers.setdefault("Content-Type", "video/mp4")
        result.headers.setdefault("Access-Control-Allow-Origin", "*")
        result.headers.setdefault("Access-Control-Allow-Methods", "GET, OPTIONS")
        result.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
        result.headers.setdefault("transferMode.dlna.org", "Streaming")
        result.headers.setdefault("TimeSeekRange.dlna.org", "npt=0.00-")
        result.headers.setdefault("contentFeatures.dlna.org", "DLNA.ORG_OP=01;DLNA.ORG_CI=0;")

    @staticmethod
    def _write_filename_header(result: StreamResponse, filename: str):
        result.headers.setdefault("Content-Disposition", f'inline; filename="{quote(filename)}"')

    async def _health_check_handler(self, _: Request) -> typing.Optional[Response]:
        try:
            await self._mtproto.health_check()
            return Response(status=200, text="ok")
        except ConnectionError:
            return Response(status=500, text="gone")

    async def _upnp_discovery_handler(self, _: Request) -> typing.Optional[Response]:
        result = Response(status=200)
        self._write_access_control_headers(result)
        return result

    def _feed_timeout(self, message_id: int, chat_id: int, local_token: int, size: int):
        debounce = self._stream_debounce.setdefault(
            local_token,
            AsyncDebounce(self._timeout_handler, self._config.request_gone_timeout)
        )

        debounce.update_args(message_id, chat_id, local_token, size)

    def _feed_downloaded_blocks(self, block_id: int, local_token: int):
        downloaded_blocks = self._downloaded_blocks.setdefault(local_token, set())
        downloaded_blocks.add(block_id)

    def _feed_stream_transport(self, local_token: int, transport: asyncio.Transport):
        transports = self._stream_transports.setdefault(local_token, set())
        transports.add(transport)

    def _get_stream_transports(self, local_token: int) -> typing.Set[asyncio.Transport]:
        return self._stream_transports[local_token] if local_token in self._stream_transports else set()

    async def _timeout_handler(self, message_id: int, chat_id: int, local_token: int, size: int):
        _debounce: typing.Optional[AsyncDebounce] = None  # avoid garbage collector

        if all(t.is_closing() for t in self._get_stream_transports(local_token)):
            blocks = (size // self._config.block_size) + 1

            if local_token in self._tokens:
                self._tokens.remove(local_token)

            remain_blocks = blocks

            if local_token in self._downloaded_blocks:
                remain_blocks = blocks - len(self._downloaded_blocks[local_token])
                del self._downloaded_blocks[local_token]

            if local_token in self._stream_debounce:
                _debounce = self._stream_debounce[local_token]
                del self._stream_debounce[local_token]

            if local_token in self._stream_transports:
                del self._stream_transports[local_token]

            remain_blocks_perceptual = remain_blocks / blocks * 100
            on_stream_closed = self._on_stream_closed

            if isinstance(on_stream_closed, OnStreamClosed):
                await on_stream_closed.handle(remain_blocks_perceptual, chat_id, message_id, local_token)

        if local_token in self._stream_debounce:
            self._stream_debounce[local_token].reschedule()

        del _debounce

    async def _stream_handler(self, request: Request) -> typing.Optional[Response]:
        _message_id: str = request.match_info["message_id"]

        if not _message_id.isdigit():
            return Response(status=401)

        _token: str = request.match_info["token"]

        if not _token.isdigit():
            return Response(status=401)

        token = int(_token)
        del _token
        message_id = int(_message_id)
        del _message_id

        local_token = serialize_token(message_id, token)

        if not self._check_local_token(local_token):
            return Response(status=403)

        range_header = request.headers.get("Range")

        if range_header is None:
            offset = 0
            data_to_skip = False
            max_size = None

        else:
            try:
                offset, data_to_skip, max_size = parse_http_range(range_header, self._config.block_size)
            except ValueError:
                return Response(status=400)

        if data_to_skip > self._config.block_size:
            return Response(status=500)

        try:
            message = await self._mtproto.get_message(int(message_id))
        except ValueError:
            return Response(status=404)

        if not isinstance(message.media, MessageMediaDocument):
            return Response(status=404)

        if not isinstance(message.media.document, Document):
            return Response(status=404)

        size = message.media.document.size
        read_after = offset + data_to_skip

        if read_after > size:
            return Response(status=400)

        if (max_size is not None) and (size < max_size):
            return Response(status=400)

        if max_size is None:
            max_size = size

        stream = StreamResponse(status=206 if (read_after or (max_size != size)) else 200)
        self._write_http_range_headers(stream, read_after, size, max_size)

        try:
            filename = mtproto_filename(message)
        except TypeError:
            filename = f"file_{message.media.document.id}"

        self._write_filename_header(stream, filename)
        self._write_access_control_headers(stream)

        await stream.prepare(request)

        while offset < max_size:
            self._feed_timeout(message_id, get_peer_id(message.peer_id), local_token, size)
            block = await self._mtproto.get_block(message, offset, self._config.block_size)
            new_offset = offset + len(block)

            if data_to_skip:
                block = block[data_to_skip:]
                data_to_skip = False

            if new_offset > max_size:
                block = block[:-(new_offset - max_size)]

            if request.transport is None:
                break

            self._feed_stream_transport(local_token, request.transport)

            if request.transport.is_closing():
                break

            await stream.write(block)
            self._feed_downloaded_blocks(offset, local_token)
            offset = new_offset

        await stream.write_eof()
