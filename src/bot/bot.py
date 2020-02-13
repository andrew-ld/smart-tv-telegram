import logging

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ConversationHandler, CommandHandler, Updater, MessageHandler, Filters, CallbackContext

from . import config
from .remote_devices import ChromecastDeviceFinder, UpnpDeviceFinder, Device


PLAY_NEW_FILE, DEVICE_SELECT = range(2)

NEW_FILE_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["play", "cancel"]
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
            ],

            states={
                PLAY_NEW_FILE: [
                    MessageHandler(Filters.regex("play"), self.play),
                    MessageHandler(Filters.regex("cancel"), self.cancel),
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
            "file ignored!"
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
                "wrong device",
                reply_markup=ReplyKeyboardRemove()
            )

            return ConversationHandler.END

        device.stop()

        device.play(
            self.config.STREAM_URL.format(
                context.user_data["current_id"]
            )
        )

        update.message.reply_text(
            f"playing {context.user_data['current_id']}",
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
                "supported devices not found in the network",
                reply_markup=ReplyKeyboardRemove()
            )

            return ConversationHandler.END

        update.message.reply_text(
            f"select device",
            reply_markup=ReplyKeyboardMarkup([
                [repr(device)]
                for device in devices
            ])
        )

        context.user_data["devices"] = devices
        return DEVICE_SELECT

    def new_movie(self, update, context: CallbackContext):
        if update.message.chat_id not in self.config.ADMIN:
            return ConversationHandler.END

        context.user_data["current_id"] = update.message.message_id

        update.message.reply_text(
            "press a button",
            reply_markup=NEW_FILE_KEYBOARD
        )

        return PLAY_NEW_FILE

    def start(self, update, *_ignored):
        update.message.reply_text("hello!")


def main():
    configuration = config.Config()
    MediaController(configuration)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
