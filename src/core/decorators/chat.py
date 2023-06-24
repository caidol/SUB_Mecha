from functools import wraps

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import CallbackContext

from src import LOGGER, dispatcher
from src.utils.groups import get_admin_permissions


def can_promote(func):
    @wraps(func)
    async def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        print("BOT ID: ", bot.id)
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message

        if update_chat_title == message_chat_title:
            cant_promote = "I can't promote members in this chat!\nMake sure I'm admin and can appoint new admins."
        else:
            cant_promote = (
                f"I can't promote people in <b>{update_chat_title}</b>!\n"
                f"Make sure I'm admin and can appoint new admins."
            )
        member = await chat.get_member(bot.id)
        if member.can_promote_members:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(cant_promote, parse_mode=ParseMode.HTML)
        
    return promote_rights