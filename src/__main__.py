import importlib
import re

from src import (
    LOGGER,
    PROGRAM_NAME,
    BOT_USERNAME,
    REPOSITORY,
    dispatcher,
)

from telegram import Update
from telegram.ext import CallbackQueryHandler, filters

from src.utils.performance import sys_status

# Current structure of the main file:
"""
func start_bot() -> To start the bot and get all its modules.
"""


async def start_bot():
    pass


async def system_status_callback(update: Update):
    text = await sys_status()

    # Callback Queries need to be answered, even if no notification to the user is needed
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(text=text)

if __name__ == '__main__':

    dispatcher.add_handler(CallbackQueryHandler(sys_status, pattern='system_status_callback'))