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


async def user_admin_check(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    chat_member_count = await chat.get_member_count()
    chat_admins = await chat.get_administrators()

    all_admins = True if len(chat_admins) == chat_member_count else False

    if chat.type == "private" or all_admins:
        return True
    
    if not member:
        member = await chat.get_member(user_id)
    else:
        #return await member.status in ("administrator", "creator")
        return await member.status in ("administrator", "creator")

def user_is_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        chat = update.effective_chat
        user = update.effective_user

        if user and user_admin_check(chat, user.id):
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass
        else:
            await update.effective_message.reply_text(
                "Who dareth summonth thy commands of admins without being an admin thyself!?"
            )

    return is_admin

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

def can_pin(func):
    @wraps(func)
    async def pin_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        message = update.effective_message
        update_chat_title = chat.title
        message_chat_title = message.chat.title

        if update_chat_title == message_chat_title:
            cant_pin = "I can't pin/unpin messages here!\nMake sure that I'm admin and have the correct privileges."
        else:
            cant_pin = f"I can't pin/unpin messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and can pin/unpin messages there."

        bot_member = await chat.get_member(bot.id)

        if bot_member.can_pin_messages:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_pin,
                parse_mode=ParseMode.HTML,
            )
    
    return pin_rights

def can_invite(func):
    @wraps(func)
    async def invite_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        message = update.effective_message
        update_chat_title = chat.title
        message_chat_title = message.chat.title

        if update_chat_title == message_chat_title:
            cant_invite = "I can't send invite links here!\nMake sure I'm admin and have the correct privileges."
        else:
            cant_invite = f"I can't send invite links in <b>{update_chat_title}</b>!\nMake sure I'm admin and can pin/unpin messages there."

        bot_member = await chat.get_member(bot.id)

        if bot_member.can_invite_users:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_invite,
                parse_mode=ParseMode.HTML,
            )
    
    return invite_rights

def can_restrict_members(func):
    @wraps(func)
    async def restriction_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        message = update.effective_message
        update_chat_title = chat.title
        message_chat_title = message.chat.title

        if update_chat_title == message_chat_title:
            cant_restrict = "I can't restrict members here!\nMake sure I'm admin and have the correct privileges."
        else:
            cant_restrict = f"I can't restrict members in <b>{update_chat_title}</b>!\nMake sure I'm admin and can restrict members there."

        bot_member = await chat.get_member(bot.id)

        if bot_member.can_restrict_members:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_restrict,
                parse_mode=ParseMode.HTML,
            )
    
    return restriction_rights

def can_delete_messages(func):
    @wraps(func)
    async def deletion_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat = update.effective_chat
        message = update.effective_message
        update_chat_title = chat.title
        message_chat_title = message.chat.title 

        if update_chat_title == message_chat_title:
            cant_delete = "I can't delete messages here!\nMake sure I'm admin and have the correct privileges."
        else:
            cant_delete = f"I can't delete messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and can delete messages here."

        bot_member = await chat.get_member(bot.id)

        if bot_member.can_delete_messages:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_delete,
                parse_mode=ParseMode.HTML,
            )
    
    return deletion_rights