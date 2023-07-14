import asyncio
import re
import html

from telegram import Update, ChatPermissions, Message, Chat
from telegram.constants import ParseMode
from telegram.error import RetryAfter, BadRequest
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters, CallbackContext

from src import LOGGER, dispatcher
from src.core.decorators.chat import can_promote, bot_is_admin, user_is_admin, can_pin, can_invite
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
/promote - Promote a chat member (done)
/demote - Demote a chat member (done)
/pin - Pin a message (almost done)
/unpin - Unpin a message  (almost done)
/mute - Mute a chat member
/unmute - Unmute a chat member
/tmute - Mute a chat member for a specific time
/report - Report a message to the admins
/invite - Send an invite link (done)
"""

@bot_is_admin
@user_is_admin
@can_promote
async def demote(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message = update.effective_message
    previous_message = message.reply_to_message
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        await update.message.reply_text("I can't find that user")
        return 
    if user_id == BOT_ID: # need to set the bot id
        await update.message.reply_text("I can't demote myself") # TODO ensure that the bot information is stored in the database
        return 

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
        username = f"@{username[0].username}" 
# select the username column of the first selected item
    if reason is None:
        reply_message = f"<b>{username} has been demoted.</b>"
    else:
        reply_message = f"<b>{username} has been demoted.\n\nReason: {reason}</b>"
    
    await update.message.reply_text(
        text=reply_message,
        parse_mode=ParseMode.HTML,
    )

@bot_is_admin
@user_is_admin
@can_promote
async def promote(update: Update, context: CallbackContext) -> None: # This needs to be tested
    BOT_ID = context.bot.id
    message = update.effective_message
    chat = update.effective_chat
    previous_message = message.reply_to_message
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        await update.message.reply_text("I can't find that user.")
        return 
    if user_id == BOT_ID:
        await update.message.reply_text("I can't promote myself.") # TODO ensure that the bot information is stored in the database
        return 

    bot_member = await chat.get_member(BOT_ID)

    try:
        await message.chat.promote_member(
            user_id=user_id,
            can_post_messages=bot_member.can_post_messages,
            can_edit_messages=bot_member.can_edit_messages,
            can_delete_messages=bot_member.can_delete_messages,
            can_invite_users=bot_member.can_invite_users,
            can_restrict_members=bot_member.can_restrict_members,
            can_pin_messages=bot_member.can_pin_messages,
            can_promote_members=bot_member.can_promote_members,
            can_manage_chat=bot_member.can_manage_chat,
            can_manage_video_chats=bot_member.can_manage_video_chats,
            can_manage_topics=bot_member.can_manage_topics,
        )
    except BadRequest:
        await message.reply_text(
            """
            Unable to promote. There are a few reasons why this could happen:\n
                - I don't have admin permissions.
                - Someone else has revoked or set my admin permissions.
            """
        )
        return

    if message.reply_to_message:
        username = previous_message.from_user.name
    else:
        username = get_name_by_userid(user_id)
        username = f"@{username[0].username}" 
    
    if reason is None:
        reply_message = f"<b>{username} has been promoted.</b>"
    else:
        reply_message = f"<b>{username} has been promoted.\n\nReason: {reason}</b>"

    await update.message.reply_text(
        text=reply_message,
        parse_mode=ParseMode.HTML,
    )


@bot_is_admin
@user_is_admin
@can_pin
async def pin(update: Update, context: CallbackContext) -> None:
    args = context.args 
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    is_group = (chat.type != "private" and chat.type != "channel") # groups are neither private chats or channels
    previous_message = message.reply_to_message # the previous message that the pin was replied to
    
    is_silent = True
    if len(args) >= 1 and previous_message:
        is_silent = not (
            args[0].lower() == "loud"
            or args[0].lower() == "notify"
        )

    if previous_message and is_group:
        try:
            await message.chat.pin_message(
                message_id=previous_message.id, disable_notification=is_silent,
            )
            return
        except BadRequest as excp:
            LOGGER.error("Admin: A bad request occurred when trying to pin a replied message.")
            raise excp
    # work on this later
    '''
    else:
        # send message initially
        pinned_message = ""
        for index in args:
            if args.index(index) == len(args):
                pinned_message += index
            else:
                pinned_message += f"{index} "

        reply_message = f"<b>{pinned_message}\n\nMentioned by {user.username}</b>"
        await user.send_message(
            text=reply_message,
            parse_mode=ParseMode.HTML,
        )

        try:
            await context.bot.pin_chat_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id, 
                disable_notification=is_silent,
            )
            return
        except BadRequest as excp:
            LOGGER.error("Admin: A bad request occurred when trying to pin a new message.")
            raise excp
    '''

@bot_is_admin
@user_is_admin
@can_promote
async def unpin(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    previous_message = message.reply_to_message

    try:
        await message.chat.unpin_message(
            message_id=previous_message.id,
        )
    except BadRequest as excp:
            LOGGER.error("Admin: A bad request occurred when trying to unpin a replied message.")
            raise excp

@bot_is_admin
@user_is_admin
@can_invite
async def invite(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    chat = update.effective_chat
    message = update.effective_message

    if chat.type in [chat.GROUP, chat.SUPERGROUP]:
        link = (await bot.get_chat(chat.id)).invite_link
        if not link:
            link = await bot.export_chat_invite_link(chat.id)
        text = f"Use the group invite link below: \n\n{link}"

        if message.reply_to_message:
            await message.reply_to_message.reply_text(
                text, 
                disable_web_page_preview=True, 
                disable_notification=True,
            )
        else:
            await message.reply_text(text, disable_web_page_preview=True, disable_notification=True)

if __name__ == '__main__':
    PROMOTE_HANDLER = CommandHandler("promote", promote)
    DEMOTE_HANDLER = CommandHandler("demote", demote)
    PIN_HANDLER = CommandHandler("pin", pin)
    UNPIN_HANDLER = CommandHandler("unpin", unpin)
    INVITE_HANDLER = CommandHandler("invite", invite)

    dispatcher.add_handler(PROMOTE_HANDLER)
    dispatcher.add_handler(DEMOTE_HANDLER)
    dispatcher.add_handler(PIN_HANDLER)
    dispatcher.add_handler(UNPIN_HANDLER)
    dispatcher.add_handler(INVITE_HANDLER)
    dispatcher.run_polling()