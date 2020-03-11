import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, Updater, MessageHandler, Filters, CallbackContext

from . import config
from .remote_devices import ChromecastDeviceFinder, UpnpDeviceFinder, Device


PLAY_NEW_FILE, DEVICE_SELECT = range(2)

NEW_FILE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["Play \u25B6", "Cancel \u274C"]
    ],
    one_time_keyboard=True
)


# noinspection PyMethodMayBeStatic
class MediaController:
    config: config.Config
    conv_handler: ConversationHandler

    def __init__(self, conf):
        self.config = conf
        updater = Updater(self.config.TOKEN, use_context=True)

        self.conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("start", self.start),
                MessageHandler(Filters.document, self.new_movie),
                MessageHandler(Filters.video, self.new_movie),
                MessageHandler(Filters.audio, self.new_movie),
                MessageHandler(Filters.animation, self.new_movie),
                MessageHandler(Filters.voice, self.new_movie),
                MessageHandler(Filters.video_note, self.new_movie),
            ],

            states={
                PLAY_NEW_FILE: [
                    MessageHandler(Filters.regex("Play \u25B6"), self.play),
                    MessageHandler(Filters.regex("Cancel \u274C"), self.cancel),
                ],

                DEVICE_SELECT: [
                    MessageHandler(Filters.text, self.play_selected),
                ]
            },

            fallbacks=[]
        )

        updater.dispatcher.add_handler(self.conv_handler)
        updater.start_polling()
        updater.idle()

    def cancel(self, update, *_):
        update.message.reply_text(
            "File ignored!"
        )

        return ConversationHandler.END

    def play_selected(self, update, context: CallbackContext):
        try:

            device: Device = next(
                device
                for device in context.user_data["devices"]
                if repr(device) == update.message.text
            )

        except StopIteration:
            update.message.reply_text(
                "Wrong device",
                reply_markup=ReplyKeyboardRemove()
            )

            return ConversationHandler.END

        device.stop()

        device.play(
            self.config.STREAM_URL.format(
                context.user_data["current_id"]
            ),
            context.user_data["file_name"]
        )

        update.message.reply_text(
            f"Playing \nID: {context.user_data['current_id']}",
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    def play(self, update, context: CallbackContext):
        devices = []

        if self.config.UPNP_ENABLED:
            devices.extend(UpnpDeviceFinder(self.config.UPNP_TIMEOUT, self.config.UPNP_WORKAROUND))

        if self.config.CHROMECAST_ENABLED:
            devices.extend(ChromecastDeviceFinder(self.config.CHROMECAST_TIMEOUT, self.config.CHROMECAST_WORKAROUND))

        if not devices:
            update.message.reply_text(
                "Supported devices not found in the network",
                reply_markup=ReplyKeyboardRemove()
            )

            return ConversationHandler.END

        update.message.reply_text(
            f"Select a device",
            reply_markup=ReplyKeyboardMarkup([
                [repr(device)]
                for device in devices
            ]),
            one_time_keyboard=True
        )

        context.user_data["devices"] = devices
        return DEVICE_SELECT

    def new_movie(self, update, context: CallbackContext):
        if update.message.chat_id not in self.config.ADMIN:
            return ConversationHandler.END

        context.user_data["current_id"] = update.message.message_id

        if (not (update.message.document is None)) and (not (update.message.document.file_name is None)):
            context.user_data["file_name"] = update.message.document.file_name
        else:
            context.user_data["file_name"] = ''

        if (not (update.message.audio is None)) or (not (update.message.voice is None)):
            context.user_data["file_name"] = ''

        update.message.reply_text(
            "Press a button",
            reply_markup=NEW_FILE_KEYBOARD
        )

        return PLAY_NEW_FILE

    def start(self, update, *_ignored):
        if update.message.chat_id not in self.config.ADMIN:
            update.message.reply_text("Unauthorized")
            return ConversationHandler.END

        update.message.reply_text("Send a media")


def main():
    configuration = config.Config()
    MediaController(configuration)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
