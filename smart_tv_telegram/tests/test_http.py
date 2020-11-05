import aiounittest

from pyrogram.raw.types import Message as TlMessage, MessageMediaUnsupported, MessageMediaDocument, DocumentEmpty, \
    Document
from requests import Response

from ..http import Http


class StubException(Exception):
    pass


class Stub:
    def __call__(self, *args, **kwargs):
        raise StubException()

    def __getattr__(self, item):
        raise StubException()


def _call_stack_stub_helper(callers, f):
    caller = callers.pop(0)

    if caller[0] != f:
        raise StubException()

    def c(*args, **kwargs):
        if args != caller[1]:
            raise StubException()

        if kwargs != caller[2]:
            raise StubException()

        if isinstance(caller[3], Exception):
            raise caller[3]

        return caller[3]

    if caller[4]:
        async def async_c(*args, **kwargs):
            return c(*args, **kwargs)

        return async_c

    return c


class CallStackStub:
    callers = None

    def __init__(self, callers):
        self.callers = callers

    def __getattr__(self, item):
        return _call_stack_stub_helper(self.callers, item)


class KVStub:
    def __init__(self, **kv):
        for k, v in kv.items():
            setattr(self, k, v)


class AioHttpStubRequest:
    match_info: dict
    headers: dict

    def __init__(self):
        self.match_info = dict()
        self.headers = dict()


# noinspection PyTypeChecker
class TestHttp(aiounittest.AsyncTestCase):
    async def test_http_wrong_token(self):
        http = Http(Stub(), Stub())

        request = AioHttpStubRequest()
        request.match_info["token"] = "1"
        request.match_info["message_id"] = "0"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 403)

    async def test_http_message_not_exists(self):
        mtproto = CallStackStub([("get_message", (10,), {}, ValueError(), True)])
        config = KVStub(block_size=1024)

        http = Http(mtproto, config)
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "1010"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 404)

    async def test_http_range_overflow_max_size(self):
        message = TlMessage(date=None, id=None, message=None, to_id=None)
        message.media = MessageMediaDocument()
        message.media.document = Document(id=None, access_hash=None, attributes=[], date=None,
                                          size=1023, dc_id=None, mime_type=None, file_reference=None)

        mtproto = CallStackStub([("get_message", (10,), {}, message, True)])
        config = KVStub(block_size=1024)

        http = Http(mtproto, config)
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "1010"
        request.headers["Range"] = "bytes=1090-10000/146515"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 400)

    async def test_http_message_wrong_document_type(self):
        message = TlMessage(date=None, id=None, message=None, to_id=None)
        message.media = MessageMediaDocument()
        message.media.document = DocumentEmpty(id=None)

        mtproto = CallStackStub([("get_message", (10,), {}, message, True)])
        config = KVStub(block_size=1024)

        http = Http(mtproto, config)
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "1010"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 404)

    async def test_http_messae_wrong_media_type(self):
        message = TlMessage(date=None, id=None, message=None, to_id=None)
        message.media = MessageMediaUnsupported()

        mtproto = CallStackStub([("get_message", (10,), {}, message, True)])
        config = KVStub(block_size=1024)

        http = Http(mtproto, config)
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "1010"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 404)

    async def test_http_filename_header(self):
        http = Http(Stub(), Stub())

        response = Response()
        http._write_filename_header(response, "test")

        self.assertEqual(response.headers["Content-Disposition"], "inline; filename=\"test\"")

    async def test_http_filename_header_escape(self):
        http = Http(Stub(), Stub())

        response = Response()
        http._write_filename_header(response, "t est\"")

        self.assertEqual(response.headers["Content-Disposition"], "inline; filename=\"t%20est%22\"")

    async def test_http_bad_massage_id(self):
        http = Http(Stub(), Stub())
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "aaaa"
        request.match_info["token"] = "1010"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 401)

    async def test_invalid_aiohttp_parser(self):
        http = Http(Stub(), Stub())
        request = AioHttpStubRequest()

        with self.assertRaises(KeyError):
            await http._stream_handler(request)

    async def test_http_bad_token(self):
        http = Http(Stub(), Stub())
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "aaaaa"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 401)

    async def test_http_right_token(self):
        http = Http(Stub(), Stub())
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "1010"

        with self.assertRaises(StubException):
            await http._stream_handler(request)

    async def test_http_bad_range(self):
        http = Http(Stub(), KVStub(block_size=1024))
        http.add_remote_token(10, 1010)

        request = AioHttpStubRequest()
        request.match_info["message_id"] = "10"
        request.match_info["token"] = "1010"
        request.headers["Range"] = "aaa"

        response = await http._stream_handler(request)

        self.assertEqual(response.status, 400)
