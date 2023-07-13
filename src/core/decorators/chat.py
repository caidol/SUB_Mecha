from functools import wraps

from telegram import Message, Update, Chat, ChatMember
from telegram.constants import ParseMode
from telegram.error import Forbidden
from telegram.ext import CallbackContext

from src import LOGGER, dispatcher
from src.utils.groups import get_admin_permissions


async def bot_admin_check(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    chat_member_count = await chat.get_member_count()
    chat_admins = await chat.get_administrators()

    all_admins = True if len(chat_admins) == chat_member_count else False
    
    if chat.type == "private" or all_admins:
        return True
    
    if not bot_member:
        bot_member = await chat.get_member(bot_id)

    return bot_member.status in ("administrator", "creator")
    

def bot_is_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message

        if update_chat_title == message_chat_title:
            not_admin = "I'm not an admin!\nMake sure I'm admin and can appoint new admins."
        else:
            not_admin = "I'm not an admin in <b>{update_chat_title}</b>\nMake sure I'm admin in <b>{update_chat_title}</b> and can appoint new admins."

        if await bot_admin_check(chat, bot.id):
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(not_admin, parse_mode=ParseMode.HTML)
    
    return is_admin


def user_admin_check(chat: Chat, user_id: int, member: ChatMember) -> bool:
    if chat.type == "private":
        return True
    
    #if not member:
    else:
        return member.status in ("administrator", "creator")

def user_is_admin(func):
    @wraps(func)
    def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        pass

def can_promote(func):
    @wraps(func)
    async def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message

        if update_chat_title == message_chat_title:
            cant_promote = "I can't promote/demote members in this chat!\nMake sure I'm admin and can appoint new admins."
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