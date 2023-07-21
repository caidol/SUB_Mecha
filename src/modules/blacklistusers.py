import html
import src.core.sql.blacklistusers_sql as user_blacklist_sql
from src import OWNER_ID, DEV_ID, dispatcher, LOGGER
from src.core.decorators.chat import user_is_admin
from src.utils.extraction import extract_user_only, extract_user_and_reason
from telegram import Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler
from telegram.helpers import mention_html
from telegram.constants import ParseMode

UNABLE_TO_BLACKLIST = [OWNER_ID] + DEV_ID

@user_is_admin
async def blacklist_user(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    bot = context.bot
    user_id, reason = extract_user_and_reason(update, message)

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
        target_user = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("I can't seem to find this user!")
            return
        else:
            raise
    
    user_blacklist_sql.blacklist_user(user_id, reason)
    await message.reply_text(f"I will strengthen our defences to block {target_user.first_name}")
    log_message = (
        f"#BLACKLIST\n"
        f"<b>Admin:</b> {mention_html(user_id, html.escape(user.first_name))}\n"
        f"<b>User:</b> {mention_html(target_user.id, html.escape(target_user.first_name))}"
    )
    if reason:
        log_message += f"\n<b>Reason:</b> {reason}"
    
    return log_message

@user_is_admin
async def unblacklist_user(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    user_id = extract_user_only(update, message)

    if not user_id:
        await message.reply_text("The user you specified seems to be invalid.")
        return 
    
    if user_id == bot.id:
        await message.reply_text("So you tried to make me blacklist myself? I see how it is...")
        return 
    
    try:
        target_user = bot.get_chat(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            await message.reply_text("I can't seem to find this user!")
            return 
        else:
            raise

    if user_blacklist_sql.is_user_blacklisted(user_id):
        user_blacklist_sql.unblacklist_user(user_id)
        await message.reply_text(f"I have allowed the user to enter back into the group and will lower the defences.")
        log_message = (
            f"#UNBLACKLIST\n"
            f"<b>Admin:</b> {mention_html(user_id, html.escape(user.first_name))}\n"
            f"<b>User:</b> {mention_html(target_user.id, html.escape(target_user.first_name))}"
        ) 

        return log_message
    else:
        await message.reply_text("This user does not seem to be blacklisted in the first place.")
        return 

@user_is_admin
async def blacklist_users(update: Update, context: CallbackContext) -> None:
    users = []
    bot = context.bot

    for each_user in user_blacklist_sql.list_blacklisted_users():
        current_user = bot.get_chat(each_user)
        reason = user_blacklist_sql.get_reason(each_user)

        if reason:
            users.append(
                f"• {mention_html(current_user.id, html.escape(current_user.first_name))} :- {reason}",
            )
        else:
            users.append(f"• {mention_html(current_user.id, html.escape(current_user.first_name))}")
        
    message = "<b>Blacklisted Users:</b>\n"

    if not users:
        message += "\nCurrently no one is being blacklisted yet."
    else:
        message += f"\n{users}"
    
    update.effective_message.reply_text(message, parse_mode=ParseMode.HMTL,)

if __name__ == '__main__':
    BLACKLIST_USER_HANDLER = CommandHandler("ignore", blacklist_user)
    UNBLACKLIST_USER_HANDLER = CommandHandler("notice", unblacklist_user)
    BLACKLIST_USERS_HANDLER = CommandHandler("ignorelist", blacklist_users)

    dispatcher.add_handler(BLACKLIST_USER_HANDLER)
    dispatcher.add_handler(UNBLACKLIST_USER_HANDLER)
    dispatcher.add_handler(BLACKLIST_USERS_HANDLER)