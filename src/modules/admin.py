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
from src.core.decorators.chat import can_promote, bot_is_admin, user_is_admin, can_invite, can_restrict_members, can_delete_messages
from src.core.sql.users_sql import get_name_by_userid 
from src.utils.extraction import extract_user_and_reason, extract_user_only
from src.utils.string_handling import time_formatter

admins_in_chat = {}

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

@bot_is_admin
@user_is_admin
@can_promote
async def demote(update: Update, context: CallbackContext) -> None:
    """The user's admin rights will be completely removed when demoted"""
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

# 
@bot_is_admin
@user_is_admin
@can_promote
async def promote(update: Update, context: CallbackContext) -> None: # This needs to be tested
    """
    The user will gain some admin rights but not any important ones
    if promoted. However if they're full promoted then they gain the same 
    admin rights as the bot, which makes them an admin.
    """
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

    if message.reply_to_message:
        username = previous_message.from_user.name
    else:
        username = get_name_by_userid(user_id)
        username = f"@{username[0].username}" 
    
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

# 
@bot_is_admin
@user_is_admin
@can_delete_messages
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
    """Delete the message that is replied to."""
    message: Optional[Message] = update.effective_message

    if not message.reply_to_message:
        await update.message.reply_text("Reply to a message to delete it.")
    
    await message.reply_to_message.delete()
    await message.delete()

@bot_is_admin
@user_is_admin
@can_restrict_members
async def mute(update: Update, context: CallbackContext) -> None:
    """
    A user's chat permissions will be completely removed so they will be
    unable to do any action in the chat but will still be physically present.
    """
    BOT_ID = context.bot.id
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
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
        f"🔇 User mute 🔇\n\n"
        f"<b>Muted User:</b> {chat_member.user.mention_html()}\n"
        f"<b>Muted By:</b> {message.from_user.mention_html() if message.from_user else 'Anonymous'}\n"
    )

    if args[0] == "tmute":
        if len(args) == 1: # no time specified
            await context.bot.send_message(
                chat.id,
                """It appears that you tried to set a time mute for antiflood without specifying any time. Try `/setfloodmode tmute <time_value>`.
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        split = reason.split(None, 1)
        time_length = split[0]
        time_mute_reason = split[1] if len(args) > 1 else ""
        temp_mute = await time_formatter(message, time_length)

        mute_message += f"<b>Muted For:</b> {time_length}\n"
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
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
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
    await message.reply_text(f"🔊 Unmuted {chat_member.user.mention_html()}! 🔊", parse_mode=ParseMode.HTML)

@bot_is_admin
@user_is_admin
async def unmute_callback(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    
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
    await message.reply_text(f"🔊 Unmuted {chat_member.user.mention_html()}! 🔊", parse_mode=ParseMode.HTML)


@bot_is_admin
@user_is_admin
@can_invite
async def invite(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

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

@bot_is_admin
@user_is_admin
@can_restrict_members
async def ban(update: Update, context: CallbackContext) -> None: # fix this function
    bot = context.bot
    BOT_ID = bot.id
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user_id, reason = await extract_user_and_reason(update, message)
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


@bot_is_admin
@user_is_admin
@can_restrict_members
async def unban(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
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

• `/ban <mention/username/id>` - Ban a user

• `/dban (reply)` - Delete the replied message and consequently ban the sender of that message 

• `/tban <mention/username/user_id> <time_limit>` - Ban a user for a specific time (check this)

• `/unban <mention/username/user_id>` - Unban a user 

• `/kick <mention/username/user_id>` - Kick a user 

• `/dkick (reply)` - Delete the replied message and consequently kick the sender of that message 

• `/purge (reply)` - Purge messages 

• `/purge [n] (reply)` - Purge "n" number of messages from replied message 

• `/promote <mention/username/user_id>` - Promote a chat member 

• `/fullpromote <mention/username/user_id>` - Promote a member with all rights 

• `/demote <mention/username/user_id>` - Demote a chat member 

• `/mute <mention/username/user_id>` - Mute a chat member 

• `/tmute <mention/username/user_id> <time_limit>` - Mute a chat member for a specific time (check this)

• `/unmute <mention/username/user_id>` - Unmute a chat member 

• `/invite` - Send an invite link 
"""

#TODO Idea: Put module info on repository and it will be links to the repository for each module
__module_info__ = """ 
The admin module consists of the majority of the admin features that can be used within a Telegram
group. These most notably involve banning, kicking, promoting, muting, purging etc. 

It's important to note that there are other features on this Telegram bot such as an antiflood system
and blacklists. However the reason that they are separated from the main admin features is because 
they are complex enough to contain quite a few commands and require many more database tables to handle. 
In that sense it is better if they are written separately as it makes it easier for people to read through
the source code.

Upon running one of the commands it will run the corresponding callback function asynchronously. Often the
commands in this file are similar to one another ("ban", "dban", "tban") and so they are handled by the same
function which will detect the variation and act accordingly.

Another important aspect of the admin file is that it contains timed bans and timed mutes. Due to the way it
has been coded, you can't display more than one specified time format at a time. For example, if you wanted
to mute someone for '5h 10m' that would not be possible as when the time string is handled and the time 
formatted it is only expecting either 'm', 'h' or 'd'.

Detailed command information:

[ban/dban/tban]

When running a ban. This means that the user will be removed from a chat without the possibility of being able
to join back from invite links or other non-admin users. They can however join back if they are added back into
the chat by an admin. A dban simply deletes the message that is replied to as well as banning the user that wrote
the message. A tban specifies a time limit that the user is banned for (information on format above). I have programmed 
an implementation where the bot will immediately send the user a PM that specifies how long it is tbanned for. This 
message will also contain the chat's current invite link. This way once the time has passed that the user is banned,
they are capable of clicking on the invite link and joining the group again without needing to contact an admin or 
other member to add them back. This works as long as the invite link isn't changed during that period of time.

[unban]

Similarly to tbanning someone as mentioned above. When a user is unbanned then the bot will send the user a message
containing the invite link that allows them to join back into the group. A message must either be replied to in order
to specify the user or their username/mention supplied so that their user id can be extracted from the database. If 
the person has never interacted with the bot before then the bot is forbidden to sending them a private message. In 
this case the bot ignores sending the message, meaning that the user must be added back some other way. When a user is
unbanned under the influence of a tban then it will immediately cancel the tban and enable them to join back into the 
group.

[kick, dkick]

When a user is kicked, they will be banned for a second and then immediately unbanned. Like before, a kicked user will
receive a message from the bot (if they've interacted with the bot before) and will receive an invite link to join back
into the group. The dkick simply deletes the replied message whilst also kicking the user of the original message. From
the perspective of the kicked user, it will appear that they get removed from the group and then immediately reinvited back
into it.

[purge, purge [n]]

Purging involves deleting all the messages from a replied message up until the current messages. This can be especially 
useful if there was a particular incident that lasted a certain amount of messages in the group and you would like to be
able to remove them. As well as this, specifying an integer number after the /purge command can allow it to only delete
that number of messages from the replied message. This could be more desirable over the first command when there is a 
cut-off point that you would like to stop the purging as there may be some messages that you don't want to delete.

[del]

Running delete on a message will delete the replied message. There's nothing more to do...

[promote, fullpromote]

The difference between promoting and full promoting a user is an interesting concept. When a user is promoted they will have
some privileges gained however not all. Specifically, when a user is promoted then they'll be able to post, edit, and delete 
messages, manage chats, video chats and topics as well as invite users. However, they will not be able to change info, restrict
members and promote members. These are argually the three most important permissions as it controls whether they'll be able to 
do the majority of the commands on this module. On the other hand, when a user is fully promoted then they will be given the same
permissions as the bot, and seeing that the bot must be an admin with full permissions to be able to run all of its commands properly
then the user will be given full permissions. It's important to note here that once a user is fully promoted then they will be incapable
of being demoted as they become an admin.

[demote]

When a chat member is demoted, they will have all the exact permissions as when promoting set to False. This is different when considering
it to being muted as they aren't outright incapable of sending anything, however they will find that the control they have over the group and
what they're able to do with it is practically non-existent.

[mute/tmute]

Muting a user renders them completely incapable of sending anything to the group. However, they'll still be present in the group whilst they're unmuted.
A tmute will mute the user for a period of time and then unmute them. Telegram provides a useful notice message at the bottom of their screen which lets
the user know how long they'll be muted for and at what time they can talk again. The only ways for a user to be unmuted are most likely from the time limit
running out or being manually unmuted by an admin. Another way could be from removing them and then being added back into the group (not yet tested). A user
being muted is different from a user being promoted/demoted. This is because when a user is promoted/demoted they are having their Chat Administration Rights
changed as according to the Telegram API. However, when a user is muted then they're having their own Chat Permissions reduced. The former involves the capability 
of managing the latter involves the capability of being able to send messages and media.

[unmute]

Unmuting involves giving the user full capability to send messages and media. This could give the user more privileges than they originally had even if they were 
able to send for example messages but not media. Unmuting also lifts other restrictions off of the user, such as whether they can invite other users or pin messages.
Another useful point to make is that unmuting a user applies to both muted or tmuted users. In the case of the user being tmuted then it will cancel the time that the
user was supposed to be muted for.

[invite]

Running the invite command will either generate a new invite link to send to users or send the current invite link that can also be used to invite users into the group. 
It all depends on whether an invite link is currently generated or not. Invite links are important ways that users can rejoin the group without needing to directly contact
an admin or other member to add them back in. A user would notice if they'd been banned that any spare and still generated invite links will be shown as 'This invite link has 
expired', however once they are unbanned then the invite link will work again and invite them back into the group. This is important in monitoring that users can't be invited
back into a group whilst they are banned unless by an admin user from adding them.
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