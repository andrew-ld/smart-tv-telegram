import asyncio
import logging

from smart_tv_telegram import *


async def async_main():
    config = Config("config.ini")
    mtproto = MtprotoController(config)
    http = HttpController(mtproto, config)
    bot = BotController(mtproto, config)

    bot.prepare()
    await mtproto.start()
    await http.start()


def main():
    loop = asyncio.get_event_loop()
    logging.basicConfig(level=logging.INFO)
    loop.run_until_complete(async_main())


if __name__ == "__main__":
    main()
