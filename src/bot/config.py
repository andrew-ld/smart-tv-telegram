import json
import typing


class Config:
    STREAM_URL: str
    TOKEN: str
    ADMIN: typing.List[int]

    CHROMECAST_ENABLED: bool
    UPNP_ENABLED: bool

    CHROMECAST_TIMEOUT: int
    UPNP_TIMEOUT: int

    CHROMECAST_WORKAROUND: bool
    UPNP_WORKAROUND: bool

    def __init__(self, config_path: str = "config.json"):
        config = json.load(open(config_path, "r"))

        self.ADMIN = config["admin_id"]
        self.TOKEN = config["token"]

        self.STREAM_URL = "http://" + \
                          config["server"]["listen_host"] + ":" + \
                          str(config["server"]["listen_port"]) + "/watch/?mid={}"

        self.CHROMECAST_ENABLED = config["bot"]["chromecast"]["enabled"]
        self.UPNP_ENABLED = config["bot"]["upnp"]["enabled"]

        self.CHROMECAST_TIMEOUT = config["bot"]["chromecast"]["timeout"]
        self.UPNP_TIMEOUT = config["bot"]["upnp"]["timeout"]

        self.CHROMECAST_WORKAROUND = config["bot"]["chromecast"]["workaround"]
        self.UPNP_WORKAROUND = config["bot"]["upnp"]["workaround"]
