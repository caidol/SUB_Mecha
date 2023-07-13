import asyncio
import re
import html

from telegram import Update, ChatPermissions, Message, Chat
from telegram.constants import ParseMode
from telegram.error import RetryAfter, BadRequest
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext

from src import LOGGER, dispatcher
from src.core.decorators.chat import can_promote, bot_is_admin
from src.utils.extraction import extract_user_and_reason, extract_user_only

from src.core.sql.users_sql import get_name_by_userid 

__MODULE__ = "Admin"
__HELP__ = """
/set_chat_title - Set the name of the group/channel
/set_chat_photo - Set the profile picture of the group/channel
/set_chat_description - Set the description of the group/channel
/set_user_title - Change the administrator title of an admin
/ban - Ban a user
/dban - Delete the replied message and consequently ban the sender of that message
/tban - Ban a user for a specific time
/ban_ghosts - Ban all the deleted accounts in a chat
/warn - Warn a user
/dwarn - Delete the replied message and consequently warn the sender of that message
/kick - Kick a user
/dkick - Delete the replied message and consequently kick the sender of that message
/purge - Purge messages
/purgefrom - Purge messages starting from a specific user
/purge [n] - Purge "n" number of messages from replied message
/promote - Promote a chat member
/demote - Demote a chat member
/pin - Pin a message
/mute - Mute a chat member
/unmute - Unmute a chat member
/tmute - Mute a chat member for a specific time
/report - Report a message to the admins
/invite - Send an invite link
"""

@bot_is_admin
@can_promote
async def demote(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message = update.effective_message
    previous_message = message.reply_to_message
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        return await message.reply_text("I can't find that user")
    if user_id == BOT_ID: # need to set the bot id
        return await update.message.reply_text("I can't demote myself") # TODO ensure that the bot information is stored in the database

    try:
        await message.chat.promote_member(
            user_id=user_id,
            can_change_info=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
        )
    except BadRequest:
        await message.reply_text(
            """
            Unable to demote. There are a few reasons why this could happen:\n
                - I don't have admin permissions.
                - Someone else has revoked or set my admin permissions.
            """
        )
        return

    if message.reply_to_message:
        username = previous_message.from_user.name
    else:
        username = get_name_by_userid(user_id)
        username = f"@{username[0].username}" # select the username column of the first selected item

    if reason is None:
        reply_message = f"<b>{username} has been demoted.</b>"
    else:
        reply_message = f"<b>{username} has been demoted.\n\nReason: {reason}</b>"
    
    await update.message.reply_text(
        text=reply_message,
        parse_mode=ParseMode.HTML,
    )

if __name__ == '__main__':
    DEMOTE_HANDLER = CommandHandler("demote", demote)

    dispatcher.add_handler(DEMOTE_HANDLER)
    dispatcher.run_polling()