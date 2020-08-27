#!/usr/bin/env python
import sys
import urllib.request
import urllib.error

from smart_tv_telegram import Config


def main(config: Config) -> int:
    try:
        urllib.request.urlopen(f"http://{config.listen_host}:{config.listen_port}/healthcheck")
    except urllib.error.URLError:
        return 1

    return 0


if __name__ == "__main__":
    _config = Config(sys.argv[-1])
    sys.exit(main(_config))
