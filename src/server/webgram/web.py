import typing
import tornado.web
import tornado.gen
import tornado.iostream

from pyrogram.api.types import MessageMediaDocument, Message
from tornado.ioloop import IOLoop

if typing.TYPE_CHECKING:
    from . import BareServer


class Web:
    def get_streamer(self: 'BareServer'):
        # noinspection PyAbstractClass
        class MtProtoFileStreamer(tornado.web.RequestHandler):
            __slots__ = ["bare"]
            bare: 'BareServer'

            def write_ok_headers(self):
                self.set_header("Content-Type", "video/mp4")
                self.set_header("Access-Control-Allow-Origin", "*")
                self.set_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.set_header("Access-Control-Allow-Headers", "Content-Type")
                self.set_header("transferMode.dlna.org", "Streaming")
                self.set_header("TimeSeekRange.dlna.org", "npt=0.00-")
                self.set_header("contentFeatures.dlna.org", "DLNA.ORG_OP=01;DLNA.ORG_CI=0")

            async def options(self):
                self.set_status(200)
                self.write_ok_headers()
                await self.flush()

            async def head(self):
                self.set_status(200)
                self.write_ok_headers()
                await self.flush()

            async def get(self):
                mid = self.get_argument("mid", "")

                if not mid.isdigit():
                    self.set_status(401)
                    return await self.finish()

                range_header = self.request.headers.get("Range", None)

                if range_header is None:
                    offset, data_to_skip = 0, False
                else:
                    is_error, *data = self.bare.parse_http_range(range_header)

                    if is_error:
                        code, *_ = data
                        self.set_status(code)
                        return await self.finish()

                    else:
                        offset, data_to_skip, *_ = data

                if data_to_skip > self.bare.BLOCK_SIZE:
                    self.set_status(500)
                    return await self.finish()

                message = self.bare.get_message(int(mid))

                if not isinstance(message, Message):
                    self.set_status(404)
                    return await self.finish()

                if not isinstance(message.media, MessageMediaDocument):
                    self.set_status(404)
                    return await self.finish()

                size = message.media.document.size
                read_after = offset + data_to_skip

                if read_after > size:
                    self.set_status(400)
                    return await self.finish()

                self.set_status(206 if read_after else 200)
                self.set_header("Content-Type", "video/mp4")
                self.set_header("Content-Range", f"bytes {read_after}-{size}/{size}")
                self.set_header("Accept-Ranges", "bytes")
                self.set_header("Content-Length", size)
                self.write_ok_headers()

                while offset < size:
                    part, offset = await IOLoop.current().run_in_executor(
                        None,
                        self.bare.iter_download,
                        message,
                        offset
                    )

                    if data_to_skip:
                        self.write(part[data_to_skip:])
                        data_to_skip = False

                    else:
                        self.write(part)

                    try:
                        await self.flush()
                    except tornado.iostream.StreamClosedError:
                        break

        MtProtoFileStreamer.bare = self
        return MtProtoFileStreamer
