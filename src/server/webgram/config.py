import json


class Config:
    # noinspection PyPep8Naming
    class config:
        APP_ID: int
        APP_HASH: str
        NAME: str
        HOST: str
        PORT: int

        def __init__(self, config_path: str = "config.json"):
            config = json.load(open(config_path, "r"))

            self.APP_ID = config["server"]["api"]["app_id"]
            self.APP_HASH = config["server"]["api"]["app_hash"]

            self.NAME = config["server"]["session_name"]
            self.HOST = config["server"]["listen_host"]
            self.PORT = config["server"]["listen_port"]

            self.TOKEN = config["token"]
