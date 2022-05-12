import json
import os
import requests
from pytube import YouTube
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

YOUTUBE_LINK, SELECT_RESOLUTION, DOWNLOAD_VIDEO, DOWNLOAD_AUDIO = range(4)
links_by_user = {}
streams_by_user = {}
yt_regex = "(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?"


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter any youtube video link: ")
    return YOUTUBE_LINK


def youtube_link(update: Update, context: CallbackContext):
    global links_by_user
    links_by_user[update.effective_chat.id] = update.message.text

    keyword = [["Download as Video"], ["Download as Mp3"], ["Back"]]
    update.message.reply_text(text="Choose your format: ",
                              reply_markup=ReplyKeyboardMarkup(keyboard=keyword, resize_keyboard=True,
                                                               one_time_keyboard=True))

    return SELECT_RESOLUTION


def get_size_format(b, factor=1024, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def select_resolution(update: Update, context: CallbackContext):
    global streams_by_user, links_by_user
    yt = YouTube(url=links_by_user[update.effective_chat.id])

    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
    streams_by_user[update.effective_chat.id] = streams
    keyboard = []
    for i in range(0, len(streams)):
        stream = streams[i]
        keyboard.append([f"{i + 1}. {stream.resolution} -> {get_size_format(stream.filesize)}"])
    update.message.reply_text(text="Choose your resolution: ",
                              reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True,
                                                               one_time_keyboard=True))


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
            SELECT_RESOLUTION: [MessageHandler(Filters.regex("Download as Video"), select_resolution)],
        },
        fallbacks=[CommandHandler('cancel', cancel)])

    dp.add_handler(conv_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
