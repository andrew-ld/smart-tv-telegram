import asyncio
import logging
import argparse
import os.path

from smart_tv_telegram import *


def is_valid_file(parser, arg):
    if not os.path.exists(arg):
        parser.error(f"The file {arg} does not exist!")

    return arg


async def async_main(config_path: str):
    config = Config(config_path)
    mtproto = Mtproto(config)
    http = Http(mtproto, config)
    bot = Bot(mtproto, config)

    bot.prepare()
    await mtproto.start()
    await http.start()


def main(config_path: str):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(config_path))


if __name__ == "__main__":
    _parser = argparse.ArgumentParser()
    _parser.add_argument("-c", "--config", type=lambda x: is_valid_file(_parser, x), default="config.ini")
    _parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=0)

    _args = _parser.parse_args()

    if _args.verbosity == 0:
        logging.basicConfig(level=logging.ERROR)

    elif _args.verbosity == 1:
        logging.basicConfig(level=logging.INFO)

    elif _args.verbosity == 2:
        logging.basicConfig(level=logging.DEBUG)

    main(_args.config)
