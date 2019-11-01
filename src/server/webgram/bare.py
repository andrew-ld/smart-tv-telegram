import pyrogram
import pyrogram.session
import pickle
import os.path

from . import (
    Config, Tools, Web
)

from pyrogram.api.functions.help import GetConfig
from pyrogram.api.functions.auth import ExportAuthorization, ImportAuthorization


class BareServer(Config, Tools, Web):
    __slots__ = ['client']
    client: pyrogram.Client

    def __init__(self):
        self.config = self.config()

        self.client = pyrogram.Client(
            self.config.NAME,
            api_id=self.config.APP_ID,
            api_hash=self.config.APP_HASH
        )

        self.client.bot_token = self.config.TOKEN
        self.client.start()

        config = self.client.send(GetConfig())
        dc_ids = [x.id for x in config.dc_options]
        keys_path = self.config.NAME + ".keys"

        if os.path.exists(keys_path):
            keys = pickle.load(open(keys_path, "rb"))
        else:
            keys = {}

        for dc_id in dc_ids:
            if dc_id != self.client.session.dc_id:
                if dc_id not in keys:
                    exported_auth = self.client.send(
                        ExportAuthorization(
                            dc_id=dc_id
                        )
                    )

                    session = pyrogram.session.Session(
                        self.client,
                        dc_id,
                        pyrogram.session.Auth(
                            self.client,
                            dc_id
                        ).create(),
                        is_media=True,
                    )

                    session.start()

                    session.send(
                        ImportAuthorization(
                            id=exported_auth.id,
                            bytes=exported_auth.bytes
                        )
                    )

                    keys[dc_id] = session.auth_key

                else:
                    session = pyrogram.session.Session(
                        self.client,
                        dc_id,
                        keys[dc_id],
                        is_media=True
                    )

                    session.start()
            else:
                session = pyrogram.session.Session(
                    self.client,
                    dc_id,
                    self.client.storage.auth_key(),
                    is_media=True,
                )

                session.start()

            self.client.media_sessions[dc_id] = session
            pickle.dump(keys, open(keys_path, "wb"))
