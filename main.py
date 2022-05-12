import json
import logging
import os
import requests
from pytube import YouTube, Stream
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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
    keyboard = []
    for i in range(0, len(streams)):
        stream = streams[i]
        keyboard.append([f"{i + 1}. {stream.resolution} -> {get_size_format(stream.filesize)}"])
    update.message.reply_text(text="Choose your resolution: ",
                              reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True,
                                                               one_time_keyboard=True))

    return DOWNLOAD_VIDEO


def download_video(update: Update, context: CallbackContext):
    c_id = update.effective_chat.id
    m_id = context.bot.send_message(chat_id=c_id, text="Starting download...")['message_id']

    last_progress = ""

    def on_progress(stream: Stream, chunk: bytes, bytes_remaining: int) -> None:
        nonlocal last_progress
        filesize = stream.filesize
        name = stream.title
        bytes_received = filesize - bytes_remaining
        bar_length = 25
        bars = int(bytes_received / filesize * bar_length)
        progress = f"📁 {name}\n\n\n{'▣' * bars}{(bar_length - bars) * '▢'}\n{get_size_format(bytes_received)} / {get_size_format(filesize)}"
        if progress != last_progress:
            context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                          text=progress)

            last_progress = progress

    yt = YouTube(url=links_by_user[update.effective_chat.id], on_progress_callback=on_progress)
    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
    stream_id = int(update.message.text.split('.')[0]) - 1
    download_location = streams[stream_id].download()
    context.bot.delete_message(chat_id=c_id, message_id=m_id)
    update.message.reply_text(text=f"Download complete! File saved to {download_location}",
                              reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


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
            DOWNLOAD_VIDEO: [MessageHandler(Filters.regex("."), download_video)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
