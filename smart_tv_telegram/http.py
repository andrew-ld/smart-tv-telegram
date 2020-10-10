import typing
from urllib.parse import quote

import aiohttp.web
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from pyrogram.raw.types import MessageMediaDocument, Document

from . import Config, Mtproto
from .tools import parse_http_range, mtproto_filename, serialize_token

__all__ = [
    "Http"
]


class Http:
    _mtproto: Mtproto
    _config: Config
    _tokens: typing.Set[int]

    def __init__(self, mtproto: Mtproto, config: Config):
        self._mtproto = mtproto
        self._config = config
        self._tokens = set()

    async def start(self):
        app = web.Application()
        app.add_routes([web.get("/stream/{message_id}/{token}", self._stream_handler)])
        app.add_routes([web.options("/stream/{message_id}/{token}", self._upnp_discovery_handler)])
        app.add_routes([web.put("/stream/{message_id}/{token}", self._upnp_discovery_handler)])
        app.add_routes([web.get("/healthcheck", self._health_check_handler)])

        # noinspection PyProtectedMember
        await aiohttp.web._run_app(app, host=self._config.listen_host, port=self._config.listen_port)

    def add_token(self, message_id: int, token: int):
        self._tokens.add(serialize_token(message_id, token))

    def _check_token(self, message_id: int, token: int):
        return serialize_token(message_id, token) in self._tokens

    def _write_upnp_headers(self, result: typing.Union[Response, StreamResponse]):
        result.headers.setdefault("Content-Type", "video/mp4")
        result.headers.setdefault("Access-Control-Allow-Origin", "*")
        result.headers.setdefault("Access-Control-Allow-Methods", "GET, OPTIONS")
        result.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
        result.headers.setdefault("transferMode.dlna.org", "Streaming")
        result.headers.setdefault("TimeSeekRange.dlna.org", "npt=0.00-")
        result.headers.setdefault("contentFeatures.dlna.org", "DLNA.ORG_OP=01;DLNA.ORG_CI=0;")

    def _write_filename_header(self, result: typing.Union[Response, StreamResponse], filename: str):
        result.headers.setdefault("Content-Disposition", f'inline; filename="{quote(filename)}"')

    async def _health_check_handler(self, _: Request) -> typing.Optional[Response]:
        try:
            await self._mtproto.health_check()
            return Response(status=200, text="ok")
        except ConnectionError:
            return Response(status=500, text="gone")

    async def _upnp_discovery_handler(self, _: Request) -> typing.Optional[Response]:
        result = Response(status=200)
        self._write_upnp_headers(result)
        return result

    async def _stream_handler(self, request: Request) -> typing.Optional[Response]:
        message_id: str = request.match_info["message_id"]

        if not message_id.isdigit():
            return Response(status=401)

        token: str = request.match_info["token"]

        if not token.isdigit():
            return Response(status=401)

        if not self._check_token(int(message_id), int(token)):
            return Response(status=403)

        range_header = request.headers.get("Range")

        if range_header is None:
            offset = 0
            data_to_skip = False
            max_size = None

        else:
            try:
                offset, data_to_skip, max_size = parse_http_range(
                    range_header, self._config.block_size)
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
        self._write_upnp_headers(stream)

        stream.headers.setdefault("Content-Range", f"bytes {read_after}-{max_size}/{size}")
        stream.headers.setdefault("Accept-Ranges", "bytes")
        stream.headers.setdefault("Content-Length", str(size))

        try:
            filename = mtproto_filename(message)
        except TypeError:
            filename = f"file_{message.media.document.id}"

        self._write_filename_header(stream, filename)

        await stream.prepare(request)

        while offset < max_size:
            block = await self._mtproto.get_block(message, offset, self._config.block_size)
            new_offset = offset + len(block)

            if data_to_skip:
                block = block[data_to_skip:]
                data_to_skip = False

            if new_offset > max_size:
                block = block[:-(new_offset - max_size)]

            offset = new_offset

            if request.transport.is_closing():
                break

            await stream.write(block)

        await stream.write_eof()
