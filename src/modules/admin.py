import asyncio
from datetime import datetime, timedelta
from typing import Optional
from time import time
from telegram import Update, Chat, Message, ChatPermissions, Chat, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.helpers import mention_html
from telegram.error import BadRequest, Forbidden
from telegram.ext import CommandHandler, CallbackQueryHandler, filters, CallbackContext
from src import dispatcher, DEV_ID
from src.core.decorators.chat import can_promote, bot_is_admin, user_is_admin, can_invite, can_restrict_members, can_delete_messages, is_not_blacklisted
from src.core.sql.users_sql import get_name_by_userid 
from src.utils.extraction import extract_user_and_reason, extract_user_only
from src.utils.string_handling import time_formatter

admins_in_chat = {}

# List the admins within a group -> check and update/change every hour.
async def list_admins(chat: Chat, chat_id: int):
    """Provide a list of the current admins in the chat -> updated every hour"""
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

# Completely remove a user's administration rights so they are unable to manage at all
@bot_is_admin
@user_is_admin
@can_promote
@is_not_blacklisted
async def demote(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message: Optional[Message] = update.effective_message
    previous_message = message.reply_to_message
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        await update.message.reply_text("I can't find that user.")
        return 
    if user_id == BOT_ID: # need to set the bot id
        await update.message.reply_text("I can't demote myself") # TODO ensure that the bot information is stored in the database
        return 

    try:
        await message.chat.promote_member(
            user_id=user_id,
            can_post_messages=False,
            can_change_info=False,
            can_delete_messages=False,
            can_edit_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
            can_manage_topics=False
        )
    except BadRequest:
        await message.reply_text(
            "Unable to demote. Check if I have admin privileges."
        )
        return

    if message.reply_to_message:
        username = previous_message.from_user.name
    else:
        username = get_name_by_userid(user_id)
        username = f"@{username[0].username}" 
    
    # select the username column of the first selected item
    if reason is None:
        reply_message = f"⬇️ <b>{username} has been demoted.</b> ⬇️"
    else:
        reply_message = f"⬇️ <b>{username} has been demoted. ⬇️\n\nReason: {reason}</b>"
    
    await update.message.reply_text(
        text=reply_message,
        parse_mode=ParseMode.HTML,
    )

# Either give a user full admin rights or give them partial admin rights
@bot_is_admin
@user_is_admin
@can_promote
@is_not_blacklisted
async def promote(update: Update, context: CallbackContext) -> None: # This needs to be tested
    BOT_ID = context.bot.id
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    previous_message = message.reply_to_message
    args = (update.message.text).split()
    user_id, reason = await extract_user_and_reason(update, message)

    if not user_id:
        await update.message.reply_text("I can't find that user.")
        return 
    if user_id == BOT_ID:
        await update.message.reply_text("I can't promote myself.") 
        return 

    bot_member = await chat.get_member(BOT_ID)

    # Give the user the same permissions as the bot member -> equivalent of admin
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
                "Unable to promote. Check if I have admin privileges."
            )
            return
    else:
        try:
            # Provide the user with some elevated privileges but don't set important ones
            await message.chat.promote_member(
                user_id=user_id,
                can_change_info=False,
                can_post_messages=bot_member.can_post_messages,
                can_edit_messages=bot_member.can_edit_messages,
                can_delete_messages=bot_member.can_delete_messages,
                can_invite_users=bot_member.can_invite_users,
                can_restrict_members=False,
                can_pin_messages=bot_member.can_pin_messages,
                can_promote_members=False,
                can_manage_chat=bot_member.can_manage_chat,
                can_manage_video_chats=bot_member.can_manage_video_chats,
                can_manage_topics=bot_member.can_manage_topics,
            )
        except BadRequest:
            await message.reply_text(
                "Unable to promote. Check if I have admin privileges"
            )
            return

    # Get the username according to either a replied message or retrieving the name from user id
    if message.reply_to_message:
        username = previous_message.from_user.name
    else:
        username = get_name_by_userid(user_id)
        username = f"@{username[0].username}" 
    
    # Set reason for promote/fullpromote
    if reason is None:
        if args[0] == "fullpromote":
            reply_message = f"⬆️👑 <b>{username} has been full promoted.</b> 👑⬆️"
        else:
            reply_message = f"⬆️ <b>{username} has been promoted.</b> ⬆️"
    else:
        if args[0] == "fullpromote":
            reply_message = f"⬆️ <b>{username} has been full promoted. ⬆️\n\nReason: {reason}</b>"
        else:
            reply_message = f"⬆️ <b>{username} has been promoted. ⬆️\n\nReason: {reason}</b>"
        
        reply_message = f"⬆️ <b>{username} has been promoted. ⬆️\n\nReason: {reason}</b>"

    await update.message.reply_text(
        text=reply_message,
        parse_mode=ParseMode.HTML,
    )

# Remove all messages from replied message to newest messages or if digit specified
# then remove that many messages from replied message.
@bot_is_admin
@user_is_admin
@can_delete_messages
@is_not_blacklisted
async def purge(update: Update, context: CallbackContext) -> None:
    """
    Reply to a certain message and delete every message after that until the
    newest message. An argument can be provided to specify how many messages after
    should be deleted
    """
    bot = context.bot
    message: Optional[Message] = update.effective_message
    replied_message = message.reply_to_message

    await message.delete()

    if not replied_message:
        return await update.message.reply_text("Reply to a message in order to purge from.")
    
    commands = (update.message.text).split(None, 1)

    # Check if an arguent is supplied and whether it is a digit
    if len(commands) > 1 and commands[1].isdigit(): # ensure it's correct type for [n] messages
        purge_to = replied_message.id + int(commands[1])
        if purge_to > message.id: # below the sent message
            purge_to = message.id
    else:
        purge_to = message.id 

    chat_id = message.chat.id
    purged_ids = []  

    # iterate from replied message to message to purge up to and delete
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

# Delete a replied message
@bot_is_admin
@user_is_admin
@can_delete_messages
@is_not_blacklisted
async def delete(update: Update, context: CallbackContext) -> None:
    """Delete the message that is replied to."""
    message: Optional[Message] = update.effective_message

    if not message.reply_to_message:
        await update.message.reply_text("Reply to a message to delete it.")
    
    await message.reply_to_message.delete()
    await message.delete()

# Completely remove a users permissions so that they are unable to send or perform any chat actions
@bot_is_admin
@user_is_admin
@can_restrict_members
@is_not_blacklisted
async def mute(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id, reason = await extract_user_and_reason(update, message)
    args = (message.text.split())

    # verify through a range of diferent options
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
        f"🔇 User mute 🔇\n\n"
        f"<b>Muted User:</b> {chat_member.user.mention_html()}\n"
        f"<b>Muted By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}\n"
    )

    # check arguments to determine whether a tmute was specified.
    if args[0] == "/tmute":
        if len(args) == 1: # no time specified
            await context.bot.send_message(
                chat.id,
                """It appears that you tried to set a time mute for antiflood without specifying any time. Try `/setfloodmode tmute <time_value>`.
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        # split the length specified and potential reason if any
        split = reason.split(None, 1)
        time_length = split[0]
        time_mute_reason = split[1] if len(split) > 1 else ""
        temp_mute = await time_formatter(message, time_length)

        mute_message += f"<b>Muted For:</b> {time_length}\n"
        if time_mute_reason:
            mute_message += f"<b>Reason:</b> {time_mute_reason}"

        try:
            # attempt to restrict the chat member util the chosen date and reply with a text
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
        # add a reason if specified
        mute_message += f"<b>Reason:</b> {reason}"
    await message.chat.restrict_member(
        user_id,
        permissions=ChatPermissions(),
    )
    await message.reply_text(mute_message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# Lift all the chat permissions on a user so they'll be able to send things in the chat again.
@bot_is_admin
@user_is_admin
@can_restrict_members
@is_not_blacklisted
async def unmute(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id = await extract_user_only(update, message) # extract only the user id
    if not user_id:
        return await update.message.reply_text("I can't find that user.")

    # set all chat permissions to true
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
    await message.reply_text(f"🔊 Unmuted {chat_member.user.mention_html()}! 🔊", parse_mode=ParseMode.HTML)

# The callback provided by pressing the unmute button below the muted user message
@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def unmute_callback(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    
    callback_query = update.callback_query
    await callback_query.answer()
    
    # split the callback data to check if it's correct 
    args = (callback_query.data).split('_')
    if args[0] == "unmute":
        user_id = args[1]

    if not user_id:
        return await update.message.reply_text("I can't find that user.")
    
    # set all the chat permissions to true
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
    await message.reply_text(f"🔊 Unmuted {chat_member.user.mention_html()}! 🔊", parse_mode=ParseMode.HTML)

# Generate an invite link or get the current invite link and send to user
@bot_is_admin
@user_is_admin
@can_invite
@is_not_blacklisted
async def invite(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

    # determine that the chat type isn't private or a channel
    if chat.type in [chat.GROUP, chat.SUPERGROUP]:
        link = (await bot.get_chat(chat.id)).invite_link
        if not link:
            link = await bot.export_chat_invite_link(chat.id)
        text = f"📬 Use the group invite link below: 📬\n\n{link}"

        if message.reply_to_message:
            await message.reply_to_message.reply_text(
                text, 
                disable_web_page_preview=True, 
                disable_notification=True,
            )
        else:
            await message.reply_text(text, disable_web_page_preview=True, disable_notification=True)

# Get the user and then ban -> means they're unable to be added back to the group
@bot_is_admin
@user_is_admin
@can_restrict_members
@is_not_blacklisted
async def ban(update: Update, context: CallbackContext) -> None: # fix this function
    bot = context.bot
    BOT_ID = bot.id
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id, reason = await extract_user_and_reason(update, message) # retrieve the user and potential reason
    args = (message.text.split())

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
            banned_user = mention.user
        else:
            banned_user = mention.user
    except IndexError: # a replied message instead
        banned_user = (
            message.reply_to_message.from_user
            if message.reply_to_message
            else "Anonymous"
        )

    ban_message = (
        f"🚫 User ban 🚫\n\n"
        f"<b>Banned User:</b> {mention_html(banned_user.id, banned_user.first_name)}\n"
        f"<b>Banned By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}\n"
    )

    # Check arguments to determine whether more processes must be carried out
    if args[0] == "/dban":
        await message.reply_to_message.delete()
    if args[0] == "/tban":
        if len(args) <= 2: # no time specified
            await context.bot.send_message(
                chat.id,
                """It appears that you tried to set a time ban for antiflood without specifying any time. Try `/tban <mention/username/id> <time_value>`.
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                parse_mode=ParseMode.MARKDOWN,
            )
            return 
        split = reason.split(None, 1)
        time_length = split[0]
        time_ban_reason = split[1] if len(split) > 1 else ""
        temp_ban = await time_formatter(message, time_length)

        ban_message += f"<b>Banned For:</b> {time_length}\n"
        # add reason if any
        if time_ban_reason:
            ban_message += f"<b>Reason:</b> {time_ban_reason}"

        if len(time_length[:-1]) < 3:
            await message.chat.ban_member(user_id, until_date=temp_ban)
            await update.message.reply_text(ban_message, parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("You cant use more than 99.")
            return
        
        if time_length[-1] == "m":
            time_later = datetime.now() + timedelta(minutes=int(time_length[:-1]))
        elif time_length[-1] == "h":
            time_later = datetime.now() + timedelta(hours=int(time_length[:-1]))
        elif time_length[-1] == "d":
            time_later = datetime.now() + timedelta(days=int(time_length[:-1]))

        link = (await bot.get_chat(chat.id)).invite_link
        if not link:
            link = await bot.export_chat_invite_link(chat.id)
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"""🚫 You have been temporarily banned! 🚫

You will be able to rejoin the group via the invite link: {link}

The time you will be unbanned after is:\n\n `{datetime.strftime(time_later, "%d %B %Y %H:%M")}`
                """,
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception in (BadRequest, Forbidden):
            pass
        return
    if reason:
        ban_message += f"</b>Reason:</b> {reason}"

    await message.chat.ban_member(user_id)
    await update.message.reply_text(ban_message, parse_mode=ParseMode.HTML)

# Unban a user and send them a message to invite them back into the chat with the current invite link
@bot_is_admin
@user_is_admin
@can_restrict_members
@is_not_blacklisted
async def unban(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    args = (update.message.text).split()
    
    reply = message.reply_to_message

    # check if the reply is a channel reply
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

    # determine if the group isn't private or a channel
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

# ban a user for a second and then immediately unban them -> send an invite link to join group
@bot_is_admin
@user_is_admin
@can_restrict_members
@is_not_blacklisted
async def kick(update: Update, context: CallbackContext) -> None:
    BOT_ID = context.bot.id
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
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
    kick_message = (
        f"⚠️ User kick ⚠️\n\n"
        f"<b>Kicked User:</b> {mention.user.mention_html()}"
        f"<b>Kicked By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}"
    )
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

    # determine if the chat isn't private or a channel
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

__module_name__ = "Admin"
__help__ = """
• `/del (reply)` - Delete a replied message 

*Admin only:* 

• `/ban <mention/username/id> <reason|Optional>` - Ban a user

• `/dban <reason|Optional> (reply)` - Delete the replied message and consequently ban the sender of that message 

• `/tban <mention/username/user_id> <time_limit> <reason|Optional>` - Ban a user for a specific time (check this)

• `/unban <mention/username/user_id>` - Unban a user 

• `/kick <mention/username/user_id> <reason|Optional>` - Kick a user 

• `/dkick <reason|Optional> (reply)` - Delete the replied message and consequently kick the sender of that message 

• `/purge (reply)` - Purge messages 

• `/purge [n] (reply)` - Purge "n" number of messages from replied message 

• `/promote <mention/username/user_id> <reason|Optional>` - Promote a chat member 

• `/fullpromote <mention/username/user_id> <reason|Optional>` - Promote a member with all rights 

• `/demote <mention/username/user_id> <reason|Optional>` - Demote a chat member 

• `/mute <mention/username/user_id> <reason|Optional>` - Mute a chat member 

• `/tmute <mention/username/user_id> <time_limit> <reason|Optional>` - Mute a chat member for a specific time (check this)

• `/unmute <mention/username/user_id>` - Unmute a chat member 

• `/invite` - Send an invite link 
"""

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
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(INVITE_HANDLER)