import logging
import os
import youtube_dl
from mutagen.easyid3 import EasyID3
import subprocess
from humanfriendly import format_timespan
from pytube import YouTube, Stream
import time
from telegram import (Update,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, ChatAction)
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    Filters,
    ConversationHandler,
)
import urllib.request

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

YOUTUBE_LINK, SELECT_RESOLUTION, DOWNLOAD_VIDEO, DOWNLOAD_MP3 = range(4)
links_by_user = {}
messages_by_user = {}
last_sent_message = {}
streams_by_user = {}
yt_regex = "(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/?.*(?:watch|embed)?(?:.*v=|v\/|\/)([\w\-_]+)\&?"

map_i2e = {0: '0️⃣', 1: '1️⃣', 2: '2️⃣', 3: '3️⃣', 4: '4️⃣', 5: '5️⃣', 6: '6️⃣', 7: '7️⃣', 8: '8️⃣', 9: '9️⃣'}


def start(update: Update, context: CallbackContext):
    update.message.reply_text("Please enter any youtube video link: ", quote=True)
    return YOUTUBE_LINK


def youtube_link(update: Update, context: CallbackContext):
    global links_by_user, messages_by_user, last_sent_message
    links_by_user[update.effective_chat.id] = update.message.text
    messages_by_user[update.effective_chat.id] = update.message.message_id
    keyword = [["📹 Download Video"], ["🎧 Download Mp3"], ["❌ Exit"]]
    last_sent_message[update.effective_chat.id] = update.message.reply_text(text="Choose your format: ",
                                                                            reply_markup=ReplyKeyboardMarkup(
                                                                                keyboard=keyword, resize_keyboard=True,
                                                                                one_time_keyboard=True),
                                                                            quote=True).message_id

    return SELECT_RESOLUTION


def get_size_format(b, factor=1024, suffix="B"):
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def select_resolution(update: Update, context: CallbackContext):
    global last_sent_message
    c_id = update.effective_chat.id
    context.bot.delete_message(chat_id=c_id, message_id=last_sent_message[c_id])
    context.bot.delete_message(chat_id=c_id, message_id=update.message.message_id)

    context.bot.send_chat_action(chat_id=c_id, action=ChatAction.TYPING)
    global streams_by_user, links_by_user
    yt = YouTube(url=links_by_user[c_id])
    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
    keyboard = []
    for i in range(0, len(streams)):
        stream = streams[i]
        keyboard.append([f"{map_i2e[i + 1]} {stream.resolution}  -  {get_size_format(stream.filesize)}"])
    keyboard.append(["❌ Exit"])
    msg_id = context.bot.send_message(chat_id=c_id, text="Choose resolution: ",
                                      reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True,
                                                                       one_time_keyboard=True))[
        'message_id']

    last_sent_message[c_id] = msg_id
    return DOWNLOAD_VIDEO


def select_bitrate(update: Update, context: CallbackContext):
    global last_sent_message
    c_id = update.effective_chat.id
    context.bot.delete_message(chat_id=c_id, message_id=last_sent_message[c_id])
    context.bot.delete_message(chat_id=c_id, message_id=update.message.message_id)

    context.bot.send_chat_action(chat_id=c_id, action=ChatAction.TYPING)
    streams = YouTube(url=links_by_user[c_id]).streams.filter(only_audio=True,
                                                              file_extension='mp4').order_by(
        'abr').desc()
    keyboard = []
    for i in range(0, len(streams)):
        stream = streams[i]
        keyboard.append([f"{map_i2e[i + 1]} {stream.abr}  -  {get_size_format(stream.filesize)}"])
    keyboard.append(["❌ Exit"])
    msg_id = context.bot.send_message(chat_id=c_id, text="Choose bitrate: ",
                                      reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True,
                                                                       one_time_keyboard=True))['message_id']
    last_sent_message[c_id] = msg_id
    return DOWNLOAD_MP3


def download_mp3(update: Update, context: CallbackContext):
    c_id = update.effective_chat.id
    context.bot.delete_message(chat_id=c_id, message_id=last_sent_message[c_id])
    context.bot.delete_message(chat_id=c_id, message_id=update.message.message_id)

    m_id = update.message.reply_text(text="Starting download...").message_id
    last_progress = ""
    dots = 1

    def on_progress(stream: Stream, chunk: bytes, bytes_remaining: int) -> None:
        nonlocal last_progress, dots
        filesize = stream.filesize
        bytes_received = filesize - bytes_remaining
        bar_length = 25
        bars = int(bytes_received / filesize * bar_length)
        progress = f"Downloading{dots * '.'}\n\n{'▣' * bars}{(bar_length - bars) * '▢'}\n{get_size_format(bytes_received)} / {get_size_format(filesize)}"
        if progress != last_progress:
            context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                          text=progress)
            last_progress = progress
        dots += 1
        dots %= 4

    yt = YouTube(url=links_by_user[c_id], on_progress_callback=on_progress)
    name = yt.title
    length = yt.length
    duration = format_timespan(length)
    streams = yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc()
    stream_id = int(update.message.text[:1]) - 1
    video_name = name + ".mp4"
    mp3_name = name + ".mp3"
    mp3_size = length * 16
    streams[stream_id].download()
    context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                  text=f"Download complete!\n\nStarting conversion to mp3...")
    bash_command = f"ffmpeg -i \"{video_name}\" -vn -ar 44100 -ac 2 -b:a 128k \"{mp3_name}\""
    process = subprocess.Popen(bash_command, cwd=os.getcwd(),
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               shell=True,
                               universal_newlines=True)

    last_time = time.time()
    context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                  text=f"Converting\n\n{'▢' * 25}")
    dots = 1
    for line in process.stdout:
        if line.startswith('size'):
            mp3_converted_size = int(line.split()[1][:-2])
            bar_length = 25
            bars = int(mp3_converted_size / mp3_size * bar_length)
            progress = f"{'▣' * bars}{(bar_length - bars) * '▢'}"
            diff = time.time() - last_time
            if diff >= 1:
                context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                              text=f"Converting{dots * '.'}\n\n{progress}")
                last_time = time.time()
                dots += 1
                dots %= 4

    if last_progress != '▣' * 25:
        context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                      text=f"Conversion Complete!\n\n{'▣' * 25}")

    def get_metadata():
        nonlocal mp3_title, mp3_artist
        url = links_by_user[c_id]
        ydl = youtube_dl.YoutubeDL({})
        with ydl:
            video = ydl.extract_info(url, download=False)

        if 'artist' in video:
            mp3_artist = video['artist']
        if 'track' in video:
            mp3_title = video['track']

    mp3_title, mp3_artist = yt.title, yt.author
    get_metadata()
    audio = EasyID3(mp3_name)
    audio["title"] = mp3_title
    audio["artist"] = mp3_artist
    audio.save()

    context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                  text=f"Conversion complete!\n\nSending the mp3 now...")
    context.bot.send_chat_action(chat_id=c_id, action=ChatAction.UPLOAD_AUDIO)
    context.bot.send_audio(chat_id=c_id, timeout=1000, audio=open(mp3_name, 'rb'),
                           duration=length,
                           reply_markup=ReplyKeyboardRemove(),
                           reply_to_message_id=messages_by_user[c_id],
                           caption=mp3_artist + " - " + mp3_title)
    context.bot.delete_message(chat_id=c_id, message_id=m_id)
    os.remove(video_name)
    os.remove(mp3_name)
    return ConversationHandler.END


def download_video(update: Update, context: CallbackContext):
    c_id = update.effective_chat.id
    context.bot.delete_message(chat_id=c_id, message_id=last_sent_message[c_id])
    context.bot.delete_message(chat_id=c_id, message_id=update.message.message_id)
    m_id = update.message.reply_text(text="Starting download...").message_id

    last_progress = ""

    def on_progress(stream: Stream, chunk: bytes, bytes_remaining: int) -> None:
        nonlocal last_progress
        filesize = stream.filesize
        bytes_received = filesize - bytes_remaining
        bar_length = 25
        bars = int(bytes_received / filesize * bar_length)
        progress = f"Downloading...\n{'▣' * bars}{(bar_length - bars) * '▢'}\n{get_size_format(bytes_received)} / {get_size_format(filesize)}"
        if progress != last_progress:
            context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                          text=progress)
            last_progress = progress

    yt = YouTube(url=links_by_user[c_id], on_progress_callback=on_progress)
    name = yt.title
    length = yt.length
    duration = format_timespan(length)
    streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
    stream_id = int(update.message.text[:1]) - 1
    streams[stream_id].download()
    urllib.request.urlretrieve(yt.thumbnail_url, "thumbnail.jpg")
    context.bot.edit_message_text(chat_id=c_id, message_id=m_id,
                                  text=f"Download complete!\n\nSending the video now...")
    context.bot.send_chat_action(chat_id=c_id, action=ChatAction.UPLOAD_VIDEO)
    context.bot.send_video(chat_id=c_id, timeout=1000, video=open(streams[stream_id].default_filename, 'rb'),
                           caption=streams[stream_id].title, supports_streaming=True, duration=length,
                           reply_markup=ReplyKeyboardRemove(),
                           reply_to_message_id=messages_by_user[c_id], thumb=open("thumbnail.jpg", 'rb'))
    context.bot.delete_message(chat_id=c_id, message_id=m_id)
    os.remove(streams[stream_id].default_filename)
    os.remove("thumbnail.jpg")
    return ConversationHandler.END


def exit_it(update: Update, context: CallbackContext):
    update.message.reply_text(text="Alright!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    credentials = os.environ
    updater = Updater(credentials['tg_token'], use_context=True, base_url='185.194.218.238:8081/bot')
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), MessageHandler(Filters.regex(yt_regex), youtube_link)],
        states={
            YOUTUBE_LINK: [MessageHandler(Filters.regex(yt_regex), youtube_link)],
            SELECT_RESOLUTION: [MessageHandler(Filters.text("📹 Download Video"), select_resolution),
                                MessageHandler(Filters.text("🎧 Download Mp3"), select_bitrate),
                                MessageHandler(Filters.regex(yt_regex), youtube_link),
                                MessageHandler(Filters.text("❌ Exit"), exit_it)],
            DOWNLOAD_VIDEO: [MessageHandler(Filters.text("❌ Exit"), exit_it),
                             MessageHandler(Filters.regex(yt_regex), youtube_link),
                             MessageHandler(Filters.text, download_video)],
            DOWNLOAD_MP3: [MessageHandler(Filters.text("❌ Exit"), exit_it),
                           MessageHandler(Filters.regex(yt_regex), youtube_link),
                           MessageHandler(Filters.text, download_mp3)],
        },
        fallbacks=[],
        run_async=True
    )

    dp.add_handler(conv_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
