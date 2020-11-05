import aiounittest

from pyrogram.types import Message as BoxedMessage

from ..tools import ascii_only, parse_http_range, build_uri, serialize_token, pyrogram_filename


# noinspection PyTypeChecker
class TestTools(aiounittest.AsyncTestCase):
    def test_ascii_only(self):
        self.assertEqual(ascii_only("abcAAA123"), "abcAAA123")
        self.assertEqual(ascii_only(chr(127)), chr(127))
        self.assertEqual(ascii_only(chr(128)), "")
        self.assertEqual(ascii_only(chr(129)), "")
        self.assertEqual(ascii_only("aa" + chr(129)), "aa")

    def test_pyrogram_filename(self):
        class _NamedMedia:
            file_name: str = None

            def __init__(self, file_name: str):
                self.file_name = file_name

        document = BoxedMessage(document=_NamedMedia("doc1"), message_id=0)
        self.assertEqual(pyrogram_filename(document), "doc1")

        video = BoxedMessage(video=_NamedMedia("video1"), message_id=0)
        self.assertEqual(pyrogram_filename(video), "video1")

        audio = BoxedMessage(video=_NamedMedia("audio1"), message_id=0)
        self.assertEqual(pyrogram_filename(audio), "audio1")

        video_note = BoxedMessage(video_note=_NamedMedia("videonote1"), message_id=0)
        self.assertEqual(pyrogram_filename(video_note), "videonote1")

        animation = BoxedMessage(animation=_NamedMedia("animation1"), message_id=0)
        self.assertEqual(pyrogram_filename(animation), "animation1")

    def test_parse_http_range(self):
        self.assertEqual(parse_http_range("bytes=0-1023/146515", 1024), (0, 0, 1023))
        self.assertEqual(parse_http_range("bytes=1000-1023/146515", 1024), (0, 1000, 1023))
        self.assertEqual(parse_http_range("bytes=1090-1023/146515", 1024), (1024, 66, 1023))
        self.assertEqual(parse_http_range("bytes=1090-aaa/146515", 1024), (1024, 66, None))

        with self.assertRaises(ValueError):
            parse_http_range("", 1024)

        with self.assertRaises(ValueError):
            parse_http_range("bytes=aaaa-1023/146515", 1024)

    def test_serialize_token(self):
        self.assertEqual(serialize_token(0, 0), 0)
        self.assertEqual(serialize_token(1, 0), 1)
        self.assertEqual(serialize_token(1, 1), 18446744073709551617)
        self.assertEqual(serialize_token(1, 2), 36893488147419103233)
        self.assertEqual(serialize_token(2, 1), 18446744073709551618)
        self.assertEqual(serialize_token(2, 2), 36893488147419103234)

    def test_build_uri(self):
        class _Config:
            listen_port = 80
            listen_host = "test"

        self.assertEqual(build_uri(_Config(), 0, 0), "http://test:80/stream/0/0")
        self.assertEqual(build_uri(_Config(), 1, 0), "http://test:80/stream/1/0")
        self.assertEqual(build_uri(_Config(), 0, 1), "http://test:80/stream/0/1")
        self.assertEqual(build_uri(_Config(), 1, 1), "http://test:80/stream/1/1")
