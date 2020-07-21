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


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=lambda x: is_valid_file(parser, x), default="config.ini")
    parser.add_argument("-v", "--verbosity", type=int, choices=[0, 1, 2], default=0)

    args = parser.parse_args()

    if args.verbosity == 0:
        logging.basicConfig(level=logging.ERROR)

    elif args.verbosity == 1:
        logging.basicConfig(level=logging.INFO)

    elif args.verbosity == 2:
        logging.basicConfig(level=logging.DEBUG)

    main(args.config)


if __name__ == "__main__":
    arg_parser()
