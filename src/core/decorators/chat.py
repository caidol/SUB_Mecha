from functools import wraps
from typing import Optional

from src import LOGGER
from src.core.sql import blacklistusers_sql as blacklistusers_sql

from telegram import Update, Chat, User, Message, ChatMember
from telegram.constants import ParseMode
from telegram.ext import CallbackContext


async def bot_admin_check(chat: Chat, bot_id: int, bot_member: ChatMember = None) -> bool:
    if chat.type == "private":
        return True
    
    if not bot_member:
        bot_member = await chat.get_member(bot_id)

    return bot_member.status in ("administrator", "creator")
    

def bot_is_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat: Optional[Chat] = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message

        if update_chat_title == message_chat_title:
            not_admin = "I'm not an admin!\nMake sure I'm admin and can appoint new admins."
        else:
            not_admin = "I'm not an admin in <b>{update_chat_title}</b>\nMake sure I'm admin in <b>{update_chat_title}</b> and can appoint new admins."

        is_bot_admin = await bot_admin_check(chat, bot.id)
        if is_bot_admin:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(not_admin, parse_mode=ParseMode.HTML)
    
    return is_admin


async def user_admin_check(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == "private":
        LOGGER.info("Chat type is private")
        return True
    
    if not member:
        LOGGER.info("User is not a chat member")
        member = await chat.get_member(user_id)
    
    LOGGER.info("member status in admin or creator:")
    return member.status in ("administrator", "creator")

def is_not_blacklisted(func):
    @wraps(func)
    async def check_user_blacklists(update: Update, context: CallbackContext, *args, **kwargs):
        chat: Optional[Chat] = update.effective_chat
        user: Optional[User] = update.effective_user

        if chat.type == "PRIVATE":
            return
        if not user:
            return 
        
        if not blacklistusers_sql.is_user_blacklisted(chat.id, user.id):
            return await func(update, context, *args, **kwargs) 
        else:
            return
    
    return check_user_blacklists

def user_is_admin(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        chat: Optional[Chat] = update.effective_chat
        user: Optional[User] = update.effective_user

        is_admin = await user_admin_check(chat, user.id)
        if user and is_admin:
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass
        else:
            await update.effective_message.reply_text(
                "Who dareth summonth thy commands of admins without being an admin thyself!?"
            )

    return is_admin

def user_is_admin_no_reply(func):
    @wraps(func)
    async def is_admin(update: Update, context: CallbackContext, *args, **kwargs):
        chat: Optional[Chat] = update.effective_chat
        user: Optional[User] = update.effective_user
        
        is_admin = await user_admin_check(chat, user.id)
        if user and is_admin:
            return await func(update, context, *args, **kwargs)
        elif not user:
            pass

    return is_admin

def user_is_not_admin(func):
    @wraps(func)
    async def is_not_admin(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        user: Optional[User] = update.effective_user 
        chat: Optional[Chat] = update.effective_chat

        is_admin = await user_admin_check(chat, user.id)
        if user and not is_admin:
            return await func(update, context, *args, **kwargs)
        
    return is_not_admin

async def user_is_ban_protected(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == "private":
        return True 
    
    if not member:
        member = await chat.get_member(user_id)
    
    return member.status in ("administrator", "creator")

def can_promote(func):
    @wraps(func)
    async def promote_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat: Optional[Chat] = update.effective_chat
        update_chat_title = chat.title
        message_chat_title = update.effective_message

        if update_chat_title == message_chat_title:
            cant_promote = "I can't promote/demote members in this chat!\nMake sure I'm admin and can appoint new admins."
        else:
            cant_promote = (
                f"I can't promote people in <b>{update_chat_title}</b>!\n"
                f"Make sure I'm admin and have the correct privileges."
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
        chat: Optional[Chat] = update.effective_chat
        message: Optional[Message] = update.effective_message
        update_chat_title = chat.title
        message_chat_title = message.chat.title

        if update_chat_title == message_chat_title:
            cant_pin = "I can't pin/unpin messages here!\nMake sure that I'm admin and have the correct privileges."
        else:
            cant_pin = f"I can't pin/unpin messages in <b>{update_chat_title}</b>!\nMake sure I'm admin and have the correct privileges."

        bot_member = await chat.get_member(bot.id)

        if bot_member.can_pin_messages:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_pin,
                parse_mode=ParseMode.HTML,
            )
    
    return pin_rights

def can_change_info(func):
    @wraps(func)
    async def info_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat: Optional[Chat] = update.effective_chat
        message: Optional[Message] = update.effective_message
        update_chat_title = chat.title
        message_chat_title = message.chat.title

        if update_chat_title == message_chat_title:
            cant_change_info = "I can't change the info here!\nMake sure I'm admin and have the correct privileges."
        else:
            cant_change_info = f"I can't change the info in <b>{update_chat_title}</b>!\nMake sure I'm admin and have the correct privileges"

        bot_member = await chat.get_member(bot.id)

        if bot_member.can_change_info:
            return await func(update, context, *args, **kwargs)
        else:
            await update.effective_message.reply_text(
                cant_change_info,
                parse_mode=ParseMode.HTML,
            )
        
    return info_rights

def can_invite(func):
    @wraps(func)
    async def invite_rights(update: Update, context: CallbackContext, *args, **kwargs):
        bot = context.bot
        chat: Optional[Chat] = update.effective_chat
        message: Optional[Message] = update.effective_message
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
        chat: Optional[Chat] = update.effective_chat
        message: Optional[Message] = update.effective_message
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
        chat: Optional[Chat] = update.effective_chat
        message: Optional[Message] = update.effective_message
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