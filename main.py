import json
import os
import requests
from time import sleep
from telegram.chataction import ChatAction
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update,
                      ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    InvalidCallbackData,
    PicklePersistence,
    MessageHandler,
    Filters,
    ConversationHandler,
)

YOUTUBE_LINK, DOWNLOAD = range(2)

yt_regex = "(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?"


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter any youtube video link: ")
    return YOUTUBE_LINK


def youtube_link(update: Update, context: CallbackContext):
    keyword = [["Download as Video"], ["Download as Mp3"], ["Back"]]
    update.message.reply_text(text="Choose your format: ",
                              reply_markup=ReplyKeyboardMarkup(keyboard=keyword, resize_keyboard=True,
                                                               one_time_keyboard=True))

    return DOWNLOAD


def cancel(update: Update, context: CallbackContext):
    pass


def main():
    credentials = os.environ

    updater = Updater(credentials['tg_token'], use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            YOUTUBE_LINK: [MessageHandler(Filters.regex(yt_regex), youtube_link)],
        },
        fallbacks=[CommandHandler('cancel', cancel)])

    dp.add_handler(conv_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
