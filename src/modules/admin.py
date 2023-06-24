import asyncio
import re
import html

from telegram import Update, ChatPermissions, Message, Chat
from telegram.constants import ParseMode
from telegram.error import RetryAfter, BadRequest
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext

from src import LOGGER, dispatcher
from src.core.decorators.chat import can_promote
from src.utils.extraction import extract_user_and_reason, extract_user_only

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

# NOTE - The group management commands (e.g admin) should only be worked on after a database has been implemented.

@can_promote
async def demote(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    previous_message = message.reply_to_message
    message.reply_text("Test")
    user_id = await extract_user_only(message)
    print("USER ID: ", user_id)

    if not user_id:
        return await message.reply_text("I can't find that user")
    '''
    if user_id == BOT_ID: # need to set the bot id
        return await update.message.reply_text("I can't demote myself")
    '''
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

    username = previous_message.from_user.name
    reply_message = f"<b>{username} has been demoted.</b>"
    await update.message.reply_text(
        text=reply_message,
        parse_mode=ParseMode.HTML,
    )

if __name__ == '__main__':
    DEMOTE_HANDLER = CommandHandler("demote", demote)

    dispatcher.add_handler(DEMOTE_HANDLER)
    dispatcher.run_polling()