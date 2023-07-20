import asyncio
import re
import html
from time import time
from telegram import Update, ChatPermissions, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import RetryAfter, BadRequest, Forbidden
from telegram.helpers import mention_html
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, filters, CallbackContext
from src import LOGGER, dispatcher, DEV_ID
from src.core.decorators.chat import can_promote, bot_is_admin, user_is_admin, can_pin, can_invite, can_restrict_members, can_delete_messages
from src.core.sql.users_sql import get_name_by_userid 
from src.utils.extraction import extract_user_and_reason, extract_user_only
from src.utils.string_handling import time_formatter

__MODULE__ = "Admin"
__HELP__ = """
/set_chat_title - Set the name of the group/channel
/set_chat_photo - Set the profile picture of the group/channel
/set_chat_description - Set the description of the group/channel
/set_user_title - Change the administrator title of an admin
/ban - Ban a user (almost done)
/dban - Delete the replied message and consequently ban the sender of that message (almost done)
/tban - Ban a user for a specific time (almost done)
/unban - Unban a user (almost done)
/listban - Ban a user from groups listed in a message
/listunban - Unban a user from groups listed in a message
/ban_ghosts - Ban all the deleted accounts in a chat
/kick - Kick a user (almost done)
/dkick - Delete the replied message and consequently kick the sender of that message (almost done)
/purge - Purge messages (done)
/purge [n] - Purge "n" number of messages from replied message (done)
/del - Delete a replied message (done)
/promote - Promote a chat member (done)
/fullpromote - Promote a member with all rights (done)
/demote - Demote a chat member (done)
/pin - Pin a message (almost done)
/unpin - Unpin a message  (almost done)
/mute - Mute a chat member (done)
/tmute - Mute a chat member for a specific time (need to check)
/unmute - Unmute a chat member (done)
/invite - Send an invite link (done)
"""

admins_in_chat = {}

async def list_admins(chat: Chat, chat_id: int):
    global admins_in_chat
    if chat_id in admins_in_chat:
        check_interval = time() - admins_in_chat[chat_id]["last_updated_at"]
        if check_interval < 3600: # within an hour of last checking
            return admins_in_chat[chat_id]["data"]
    
    admin_list = await chat.get_administrators()

    admins_in_chat[chat_id] = {
        "last_updated_at": time(),
        "data": [
            member.user.id
            for member in admin_list
        ],
    }
    return admins_in_chat[chat_id]["data"]

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
    args = (update.message.text).split()
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        await update.message.reply_text("I can't find that user.")
        return 
    if user_id == BOT_ID:
        await update.message.reply_text("I can't promote myself.") # TODO ensure that the bot information is stored in the database
        return 

    bot_member = await chat.get_member(BOT_ID)

    if args[0] == "fullpromote":
        try:
            await message.chat.promote_member(
                user_id=user_id,
                can_change_info=bot_member.can_change_info,
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
    else:
        try:
            await message.chat.promote_member(
                user_id=user_id,
                can_change_info=False,
                can_post_messages=bot_member.can_post_messages,
                can_edit_messages=bot_member.can_edit_messages,
                can_delete_messages=bot_member.can_delete_messages,
                can_invite_users=bot_member.can_invite_users,
                can_restrict_members=False,
                can_pin_messages=False,
                can_promote_members=False,
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
@can_delete_messages
async def purge(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    message = update.effective_message
    replied_message = message.reply_to_message

    await message.delete()

    if not replied_message:
        return await update.message.reply_text("Reply to a message in order to purge from.")
    
    commands = (update.message.text).split(None, 1)

    if len(commands) > 1 and commands[1].isdigit(): # ensure it's correct type for [n] messages
        purge_to = replied_message.id + int(commands[1])
        if purge_to > message.id: # below the sent message
            purge_to = message.id
    else:
        purge_to = message.id 

    chat_id = message.chat.id
    purged_ids = []  

    for message_id in range(replied_message.id, purge_to):
        purged_ids.append(message_id)

        # Delete messages whilst appending if reaches max Telegram limit of 100
        if len(purged_ids) == 100:
            for to_delete_id in purged_ids:
                try:
                    await bot.delete_message(
                        chat_id=chat_id,
                        message_id=int(to_delete_id),
                    )
                except BadRequest:
                    pass

            # Start again in order to delete more than 100 messages
            purged_ids = []

    # Delete any remaining messages
    if len(purged_ids) > 0:
        for to_delete_id in purged_ids:
            try:
                await bot.delete_message(
                    chat_id=chat_id,
                    message_id=int(to_delete_id),
                )  
            except BadRequest:
                pass 

@bot_is_admin
@user_is_admin
@can_delete_messages
async def delete(update: Update, context: CallbackContext) -> None:
    message = update.effective_message

    if not message.reply_to_message:
        await update.message.reply_text("Reply to a message to delete it.")
    
    await message.reply_to_message.delete()
    await message.delete()

@bot_is_admin
@user_is_admin
@can_restrict_members
async def mute(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message = update.effective_message
    chat = update.effective_chat
    args = (update.message.text).split(None, 1)
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        return await update.message.reply_text(
            "I can't find that user"
        )
    if user_id == BOT_ID:
        return await update.message.reply_text(
            "You're trying to make me mute myself? I see how it is :("
        )
    if user_id == DEV_ID:
        return await update.message.reply_text(
            "It looks like you were trying to mute the developer of me, sorry you can't do that."
        )
    if user_id in (await chat.get_administrators()):
        return await update.message.reply_text(
            "I'm unable to mute admins - I'm afraid it's just the rules."
        )
    chat_member = (await chat.get_member(user_id))
    keyboard = [
        [InlineKeyboardButton("Unmute  🚨", callback_data=f"unmute_{user_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    mute_message = (
        f"<b>Muted User:</b> {chat_member.user.mention_html()}\n"
        f"<b>Muted By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}\n"
    )

    if args[0] == "tmute":
        split = reason.split(None, 1)
        time_length = split[0]
        time_mute_reason = split[1] if len(args) > 1 else ""
        temp_mute = await time_formatter(message, time_length)

        mute_message += f"<b>Banned For:</b> {time_length}\n"
        if time_mute_reason:
            mute_message += f"<b>Reason:</b> {time_mute_reason}"

        try:
            if len(time_length[:-1]) < 3:
                await message.chat.restrict_member(
                    user_id,
                    permissions=ChatPermissions(),
                    until_date=temp_mute
                )
                await update.message.reply_text(
                    mute_message, 
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup,
                )
            else:
                await update.message.reply_text("You cant use more than 99.")
        except AttributeError:
            pass
        return

    if reason:
        mute_message += f"<b>Reason:</b> {reason}"
    await message.chat.restrict_member(
        user_id,
        permissions=ChatPermissions(),
    )
    await message.reply_text(mute_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

@bot_is_admin
@user_is_admin
@can_restrict_members
async def unmute(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    user_id = await extract_user_only(update, message)
    if not user_id:
        return await update.message.reply_text("I can't find that user.")

    await message.chat.restrict_member(
        user_id,
        permissions= ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
        )
    )
    chat_member = (await chat.get_member(user_id))
    await message.reply_text(f"Unmuted {chat_member.user.mention_html()}!", parse_mode=ParseMode.HTML)

async def unmute_callback(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    
    callback_query = update.callback_query
    await callback_query.answer()
    
    args = (callback_query.data).split('_')
    if args[0] == "unmute":
        user_id = args[1]

    if not user_id:
        return await update.message.reply_text("I can't find that user.")
    
    await message.chat.restrict_member(
        user_id,
        permissions= ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True,
            can_manage_topics=True,
            can_send_audios=True,
            can_send_documents=True,
            can_send_photos=True,
            can_send_videos=True,
            can_send_video_notes=True,
            can_send_voice_notes=True,
        )
    )
    chat_member = (await chat.get_member(user_id))
    await message.reply_text(f"Unmuted {chat_member.user.mention_html()}!", parse_mode=ParseMode.HTML)

@bot_is_admin
@user_is_admin
@can_restrict_members
async def ban_deleted_accounts(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    chat_id = message.chat.id
    deleted_users = []
    banned_users = 0

    #TODO work on this later
    #for index in chat.get_members

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

@bot_is_admin
@user_is_admin
@can_restrict_members
async def ban(update: Update, context: CallbackContext) -> None: # fix this function
    BOT_ID = context.bot.id
    message = update.effective_message
    chat = update.effective_chat
    user_id, reason = await extract_user_and_reason(update, message)
    args = context.args

    if not user_id:
        return await update.message.reply_text(
            "I can't find that user"
        )
    if user_id == BOT_ID:
        return await update.message.reply_text(
            "You're trying to make me ban myself? I see how it is :("
        )
    if user_id == DEV_ID:
        return await update.message.reply_text(
            "It looks like you were trying to ban the developer of me, sorry you can't do that."
        )
    if user_id in (await list_admins(chat, chat.id)):
        return await update.message.reply_text(
            "I'm unable to ban admins - I'm afraid it's just the rules."
        )

    try:
        mention = (await chat.get_member(user_id))
        
        if mention.user.username is None:
            banned_user = mention.user.name
        else:
            banned_user = mention.user.username
    except IndexError: # a replied message instead
        banned_user = (
            message.reply_to_message.from_user.username
            if message.reply_to_message
            else "Anonymous"
        )

    ban_message = (
        f"<b>Banned User:</b> {mention.user.mention_html()}\n"
        f"<b>Banned By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}\n"
    )

    if args[0] == "dban":
        await message.reply_to_message.delete()
    if args[0] == "tban":
        split = reason.split(None, 1)
        time_length = split[0]
        time_ban_reason = split[1] if len(args) > 1 else ""
        temp_ban = await time_formatter(message, time_length)

        ban_message += f"<b>Banned For:</b> {time_length}\n"
        if time_ban_reason:
            ban_message += f"<b>Reason:</b> {time_ban_reason}"

        if len(time_length[:-1]) < 3:
            await message.chat.ban_member(user_id, until_date=temp_ban)
            await update.message.reply_text(ban_message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("You cant use more than 99.")
        return
    if reason:
        ban_message += f"</b>Reason:</b> {reason}"

    await message.chat.ban_member(user_id)
    await update.message.reply_text(ban_message, parse_mode=ParseMode.HTML)


@bot_is_admin
@user_is_admin
@can_restrict_members
async def unban(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    args = (update.message.text).split()
    
    reply = message.reply_to_message

    if reply and reply.sender_chat and reply.sender_chat != message.chat.id:
        return await update.message.reply_text("You cannot unban a channel.")

    if len(args) == 2:
        user = args[0]
        user_id = await extract_user_only(user)
    elif len(args) == 1 and reply:
        user_id = reply.from_user.id
    else:
        await update.message.reply_text(
            "Please either provide a username or reply to a message in order to unban someone."
        )
 
    await message.chat.unban_member(user_id)
    username = await chat.get_member(user_id)
    await update.message.reply_text(f"<b>Unbanned:</b> {username.user.mention_html()}", parse_mode=ParseMode.HTML)

    # send an invite to the user that has been unbanned
    bot = context.bot

    if chat.type in [chat.GROUP, chat.SUPERGROUP]:
        link = (await bot.get_chat(chat.id)).invite_link
        if not link:
            link = await bot.export_chat_invite_link(chat.id)
        text = f"You have been unbanned from {update.effective_chat.title}. Below is the invite link if you'd wish to rejoin:\n\n{link}"

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                disable_web_page_preview=True, 
            )
        except Forbidden:
            pass

@bot_is_admin
@user_is_admin
@can_restrict_members
async def kick(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message = update.effective_message
    chat = update.effective_chat
    user_id, reason = await extract_user_and_reason(update, message)
    args = (update.message.text).split(None, 1)

    if not user_id:
        await update.message.reply_text("I can't find that user.")
    if user_id == BOT_ID:
        return await update.message.reply_text(
            "You're trying to make me ban myself? I see how it is :("
        )
    if user_id == DEV_ID:
        return await update.message.reply_text(
            "It looks like you were trying to ban the developer of me, sorry you can't do that."
        )
    if user_id in (await list_admins(chat, chat.id)):
        return await update.message.reply_text(
            "I'm unable to ban admins - I'm afraid it's just the rules."
        )
    
    mention = (await chat.get_member(user_id))
    kick_message = f"""
<b>Kicked User:</b> {mention.user.mention_html()}
<b>Kicked By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}
    """
    if reason:
        kick_message += f"\n<b>Reason:</b> {reason}"

    if args[0] == "dkick":
        await message.reply_to_message.delete()
    await message.chat.ban_member(user_id)
    await message.reply_text(kick_message, parse_mode=ParseMode.HTML)
    await asyncio.sleep(1)
    await message.chat.unban_member(user_id)

    # send an invite to the user that has been unbanned
    bot = context.bot

    if chat.type in [chat.GROUP, chat.SUPERGROUP]:
        link = (await bot.get_chat(chat.id)).invite_link
        if not link:
            link = await bot.export_chat_invite_link(chat.id)
        text = f"You have been kicked from {update.effective_chat.title}. Below is the invite link if you'd wish to rejoin:\n\n{link}"
        
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text=text,
                disable_web_page_preview=True, 
            )
        except Forbidden:
            pass

if __name__ == '__main__':
    BAN_HANDLER = CommandHandler(
        ["ban", "dban", "tban"], ban, filters=~filters.ChatType.PRIVATE,
    )
    UNBAN_HANDLER = CommandHandler(
        "unban", unban, filters=~filters.ChatType.PRIVATE,
    )
    KICK_HANDLER = CommandHandler(
        ["kick", "dkick"], kick, filters=~filters.ChatType.PRIVATE,
    )
    MUTE_HANDLER = CommandHandler(
        ["mute", "tmute"], mute, filters=~filters.ChatType.PRIVATE,
    )
    UNMUTE_HANDLER = CommandHandler(
        "unmute", unmute,
    )
    UNMUTE_CALLBACK_HANDLER = CallbackQueryHandler(
        callback=unmute_callback, pattern="unmute_[0-9]{5,10}", 
    )
    PURGE_HANDLER = CommandHandler(
        "purge", purge, filters=~filters.ChatType.PRIVATE,
    )
    PROMOTE_HANDLER = CommandHandler(
        ["promote", "fullpromote"], promote, filters=~filters.ChatType.PRIVATE,
    )
    DEMOTE_HANDLER = CommandHandler(
        "demote", demote, filters=~filters.ChatType.PRIVATE,
    )
    PIN_HANDLER = CommandHandler(
        "pin", pin, filters=~filters.ChatType.PRIVATE,
    )
    UNPIN_HANDLER = CommandHandler(
        "unpin", unpin, filters=~filters.ChatType.PRIVATE,
    )
    DELETE_HANDLER = CommandHandler(
        "del", delete, filters=~filters.ChatType.PRIVATE,
    )
    INVITE_HANDLER = CommandHandler(
        "invite", invite, filters=~filters.ChatType.PRIVATE,
    )

    dispatcher.add_handler(BAN_HANDLER)
    dispatcher.add_handler(UNBAN_HANDLER)
    dispatcher.add_handler(KICK_HANDLER)
    dispatcher.add_handler(MUTE_HANDLER)
    dispatcher.add_handler(UNMUTE_HANDLER)
    dispatcher.add_handler(UNMUTE_CALLBACK_HANDLER)
    dispatcher.add_handler(PURGE_HANDLER)
    dispatcher.add_handler(PROMOTE_HANDLER)
    dispatcher.add_handler(DEMOTE_HANDLER)
    dispatcher.add_handler(PIN_HANDLER)
    dispatcher.add_handler(UNPIN_HANDLER)
    dispatcher.add_handler(DELETE_HANDLER)
    dispatcher.add_handler(INVITE_HANDLER)
    dispatcher.run_polling()