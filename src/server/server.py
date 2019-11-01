import tornado.web
import tornado.ioloop
import logging

from . import webgram


def main():
    server = webgram.BareServer()

    web = tornado.web.Application([
        (r"/watch/", server.get_streamer()),
    ])

    web.listen(server.config.PORT, server.config.HOST)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
