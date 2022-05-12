import json
import os
import requests
from time import sleep
from telegram.chataction import ChatAction
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton,
                      ReplyKeyboardRemove)
from telegram.ext import (Updater, CommandHandler, CallbackQueryHandler, CallbackContext, InvalidCallbackData,
                          PicklePersistence, MessageHandler, Filters, ConversationHandler,
                          )


def start(update: Update, context: CallbackContext):
    pass


def cancel(update: Update, context: CallbackContext):
    pass


def main():
    Credentials = {}
    with open('creds.json', 'r') as f:
        credentials = json.load(f)

    updater = Updater(credentials['tg_token'], use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={

        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dp.add_handler(conv_handler)
    updater.start_polling()


if __name__ == '__main__':
    main()
