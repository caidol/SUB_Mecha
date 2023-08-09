import html
from typing import Optional
import src.core.sql.blacklistusers_sql as user_blacklist_sql
from src import OWNER_ID, DEV_ID, dispatcher
from src.core.decorators.chat import bot_is_admin, user_is_admin, is_not_blacklisted
from src.utils.extraction import extract_user_only, extract_user_and_reason
from telegram import Update, Chat, User, Message
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler
from telegram.helpers import mention_html
from telegram.constants import ParseMode

UNABLE_TO_BLACKLIST = [OWNER_ID, DEV_ID]

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def blacklist_user(update: Update, context: CallbackContext) -> str:
    message: Optional[Message] = update.effective_message
    user: Optional[User] = update.effective_user
    chat: Optional[Chat] = update.effective_chat
    bot = context.bot
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        await message.reply_text("The user you specified seems to be invalid.")
        return 
    
    if user_id == bot.id:
        await message.reply_text("So you tried to make me blacklist myself? I see how it is...")
        return 
    
    if user_id in UNABLE_TO_BLACKLIST:
        await message.reply_text("Sorry, that user is too privileged to attempt to blacklist.")
        return 
    
    try:
        target_user = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("I can't seem to find this user!")
            return
        else:
            raise
    
    user_blacklist_sql.blacklist_user(chat.id, user_id, reason)
    await message.reply_text(
        f"🔇🧑 I will strengthen my defences to ignore `{target_user.user.first_name}` 🔇🧑",
        parse_mode=ParseMode.MARKDOWN,
    )
    log_message = (
        f"#BLACKLIST\n"
        f"<b>Admin:</b> {mention_html(user_id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(target_user.user.id, html.escape(target_user.user.first_name))}"
    )
    if reason:
        log_message += f"\n<b>Reason:</b> {reason}"
    
    return log_message

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def unblacklist_user(update: Update, context: CallbackContext) -> str:
    message: Optional[Message] = update.effective_message
    user: Optional[User] = update.effective_user
    chat: Optional[Chat] = update.effective_chat
    bot, args = context.bot, context.args
    user_id = await extract_user_only(update, message)

    if not user_id:
        await message.reply_text("The user you specified seems to be invalid.")
        return 
    
    if user_id == bot.id:
        await message.reply_text("So you tried to make me blacklist myself? I see how it is...")
        return 
    
    try:
        target_user = await chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("I can't seem to find this user!")
            return 
        else:
            raise

    if user_blacklist_sql.is_user_blacklisted(chat.id, user_id):
        user_blacklist_sql.unblacklist_user(chat.id, user_id)
        await message.reply_text("🧑 I will now begin to notice this user again. 🧑")
        log_message = (
            f"#UNBLACKLIST\n"
            f"<b>Admin:</b> {mention_html(user_id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(target_user.user.id, html.escape(target_user.user.first_name))}"
        ) 

        return log_message
    else:
        await message.reply_text("This user does not seem to be blacklisted in the first place.")
        return 

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def blacklist_users(update: Update, context: CallbackContext) -> None:
    users = []
    bot = context.bot
    chat: Optional[Chat] = update.effective_chat

    for each_user in user_blacklist_sql.list_blacklisted_users(chat.id):
        current_user = await chat.get_member(each_user.user_id)
        reason = user_blacklist_sql.get_reason(chat.id, current_user.user.id)

        if reason:
            users.append(
                f"• {mention_html(current_user.user.id, html.escape(current_user.user.first_name))} :- {reason}",
            )
        else:
            users.append(f"• {mention_html(current_user.user.id, html.escape(current_user.user.first_name))}")
        
    message = "<b>Blacklisted Users:</b>\n"

    if not users:
        message += "\nCurrently no one is being blacklisted yet."
    else:
        for user, _ in enumerate(users):
            message += f"\n{users[user]}"
    
    await update.effective_message.reply_text(message, parse_mode=ParseMode.HTML)

def __migrate__(old_chat_id, new_chat_id):
    user_blacklist_sql.migrate_chat(old_chat_id, new_chat_id)

__module_name__ = "BlacklistUsers"
__help__ = """
*Admin only:*

• `/ignore <mention/username/id>` - Ignore a user and don't respond to any command calls

• `/notice <mention/username/id>` - Notice a user and respond to command calls

• `/ignorelist` - Provide a list of all the ignored users in a chat
"""

BLACKLIST_USER_HANDLER = CommandHandler("ignore", blacklist_user)
UNBLACKLIST_USER_HANDLER = CommandHandler("notice", unblacklist_user)
BLACKLIST_USERS_HANDLER = CommandHandler("ignorelist", blacklist_users)

dispatcher.add_handler(BLACKLIST_USER_HANDLER)
dispatcher.add_handler(UNBLACKLIST_USER_HANDLER)
dispatcher.add_handler(BLACKLIST_USERS_HANDLER)