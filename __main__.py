import asyncio
import logging
import sys

from smart_tv_telegram import *


async def async_main():
    config = Config("config.ini")
    mtproto = Mtproto(config)
    http = Http(mtproto, config)
    bot = Bot(mtproto, config)

    bot.prepare()
    await mtproto.start()
    await http.start()


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "debug":
            logging.basicConfig(level=logging.DEBUG)

        elif sys.argv[1] == "production":
            logging.basicConfig(level=logging.ERROR)

        else:
            raise ValueError("expected debug or production")
    else:
        logging.basicConfig(level=logging.INFO)

    main()
