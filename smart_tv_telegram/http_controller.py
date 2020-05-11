import typing

import aiohttp.web
from aiohttp import web
from aiohttp.web_request import Request
from aiohttp.web_response import Response, StreamResponse
from pyrogram.api.types import MessageMediaDocument

from smart_tv_telegram import Config
from smart_tv_telegram import MtprotoController
from smart_tv_telegram.tools import parse_http_range


class HttpController:
    _mtproto: MtprotoController
    _config: Config

    def __init__(self, mtproto: MtprotoController, config: Config):
        self._mtproto = mtproto
        self._config = config

    async def start(self):
        app = web.Application()
        app.add_routes([web.get("/stream/{message_id}", self._stream_handler)])
        app.add_routes([web.options("/stream/{message_id}", self._fake_headers)])
        app.add_routes([web.put("/stream/{message_id}", self._fake_headers)])

        await aiohttp.web._run_app(app, host=self._config.listen_host, port=self._config.listen_port)

    def _write_headers(self, result: typing.Union[Response, StreamResponse]) -> typing.NoReturn:
        result.headers.setdefault("Content-Type", "video/mp4")
        result.headers.setdefault("Access-Control-Allow-Origin", "*")
        result.headers.setdefault("Access-Control-Allow-Methods", "GET, OPTIONS")
        result.headers.setdefault("Access-Control-Allow-Headers", "Content-Type")
        result.headers.setdefault("transferMode.dlna.org", "Streaming")
        result.headers.setdefault("TimeSeekRange.dlna.org", "npt=0.00-")
        result.headers.setdefault("contentFeatures.dlna.org", "DLNA.ORG_OP=01;DLNA.ORG_CI=0;")

    # noinspection PyUnusedLocal
    async def _fake_headers(self, request: Request) -> typing.Optional[Response]:
        result = Response(status=200)
        self._write_headers(result)
        return result

    async def _stream_handler(self, request: Request) -> typing.Optional[Response]:
        message_id: str = request.match_info["message_id"]

        if not message_id.isdigit():
            return Response(status=401)

        range_header = request.headers.get("Range")

        if range_header is None:
            offset = 0
            data_to_skip = False

        else:
            try:
                offset, data_to_skip = parse_http_range(
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

        size = message.media.document.size
        read_after = offset + data_to_skip

        if read_after > size:
            return Response(status=400)

        stream = StreamResponse(status=206 if read_after else 200)
        stream.headers.setdefault(
            "Content-Range", f"bytes {read_after}-{size}/{size}")
        stream.headers.setdefault("Accept-Ranges", "bytes")
        stream.headers.setdefault("Content-Length", str(size))
        self._write_headers(stream)
        await stream.prepare(request)

        while offset < size:
            block = await self._mtproto.get_block(message, offset, self._config._block_size)
            offset += len(block)

            if data_to_skip:
                block = block[data_to_skip:]
                data_to_skip = False

            if request.transport.is_closing():
                break

            await stream.write(block)

        await stream.write_eof()
