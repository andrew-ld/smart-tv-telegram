import asyncio
import configparser
import logging
import argparse
import os.path

from smart_tv_telegram import *


def open_config(parser: argparse.ArgumentParser, arg: str) -> Config:
    if not os.path.exists(arg):
        parser.error(f"The file `{arg}` does not exist")

    elif not os.path.isfile(arg):
        parser.error(f"`{arg}` is not a file")

    try:
        return Config(arg)
    except ValueError as err:
        parser.error(str(err))
    except KeyError as err:
        parser.error(f"config key {str(err)} does not exists")
    except configparser.Error as err:
        parser.error(f"generic configparser error:\n{str(err)}")


async def async_main(config: Config):
    mtproto = Mtproto(config)
    http = Http(mtproto, config)

    bot = Bot(mtproto, config, http)
    bot.prepare()

    await mtproto.start()
    await http.start()


def main(config: Config):
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(config))


def arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", type=lambda x: open_config(parser, x), default="config.ini")
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
