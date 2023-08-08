from typing import Optional
from io import BytesIO

from telegram import Update, Chat, Message
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)
import src.core.sql.users_sql as users_sql
from src import LOGGER, DEV_ID, dispatcher

USERS_GROUP = 4
CHAT_GROUP = 5

LOGGER.info("Users: Started initialisation.")

def get_user_id(username, chat_id):
    LOGGER.info("Users: Retrieving the user id given username.")

    if username.startswith("@"):
        username = username[1:]
    
    if len(username) <= 5:
        return None

    LOGGER.info("Users: Querying users_sql for userid given username")
    users = users_sql.get_userid_by_name(username)
    

    if not users: # No users are present
        LOGGER.info("Users: No users are present.")
        return None
    elif len(users) == 1:
        return users[0].user_id
    else:
        # We are going to loop through the list of users and find the username given the user_id
        for user_object in users:
            try:
                user_data = dispatcher.bot.get_chat(chat_id)
                if user_data.username == username:
                    return user_data.id
            except BadRequest as excp:
                if excp.message == "Chat not found":
                    LOGGER.error("Users: Unable to find chat.")
                else:
                    LOGGER.error("Users: Error extracting User ID.")
    return None

async def broadcast(update: Update, context: CallbackContext):
    LOGGER.info("Users: Broadcasting message.")
    message: Optional[Message] = update.effective_message
    if message.from_user.id != DEV_ID:
        return await message.reply_text("You must be the developer user to be able to send this!")
    
    to_send = message.text.split(None, 1)

    if len(to_send) >= 2:
        group_broadcast = False
        user_broadcast = False

        if to_send[0] == "/broadcastgroups":
            group_broadcast = True
        elif to_send[0] == "/broadcastusers":
            user_broadcast = True
        elif to_send[0] == "/broadcastall":
            group_broadcast = user_broadcast = True

        all_chats = users_sql.get_all_chats() or []
        all_users = users_sql.get_all_users() or []
        failed_groups = 0
        failed_users = 0

        if group_broadcast:
            LOGGER.info("Users: Sending out a group broadcast.")
            for group in all_chats:
                try:
                    context.bot.sendMessage(
                        int(group.chat_id),
                        to_send[1],
                        parse_mode = "MARKDOWN",
                        disable_web_page_preview = True,
                    )
                except TelegramError: 
                    failed_groups += 1
        
        if user_broadcast:
            LOGGER.info("Users: Sending out a user broadcast.")
            for user in all_users:
                try:
                    context.bot.sendMessage(
                        int(user.user_id),
                        to_send[1],
                        parse_mode = "MARKDOWN",
                        disable_web_page_preview = True,
                    )
                except TelegramError:
                    failed_users += 1
        
        update.effective_message.reply_text(
            f"📡 Broadcast message complete. \nGroups failed `{failed_groups}` \nFailed users `{failed_users}` 📡 "
        )

async def chats(update: Update, context: CallbackContext):
    all_chats = users_sql.get_all_chats() or []
    chatfile = "List of chats.\n0. Chat name | Chat ID | Members count\n"
    P = 1
    for chat in all_chats:
        try:
            curr_chat = await context.bot.getChat(chat.chat_id)
            bot_member = await curr_chat.get_member(context.bot.id)
            chat_members = await curr_chat.get_members_count(context.bot.id)
            chatfile += "{}. {} | {} | {}\n".format(
                P, chat.chat_name, chat.chat_id, chat_members,
            )
            P = P + 1
        except:
            pass

    with BytesIO(str.encode(chatfile)) as output:
        output.name = "groups_list.txt"
        await update.effective_message.reply_document(
            document=output,
            filename="groups_list.txt",
            caption="Here be the list of groups in my database.",
        ) 

async def log_user(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

    if message.reply_to_message:
        LOGGER.info("Users: User is being logged from a replied message.")
        users_sql.update_user(
            message.reply_to_message.from_user.id,
            message.reply_to_message.from_user.username,
            chat.id,
            chat.title,
        )
        return
    
    if message.forward_from:
        LOGGER.info("Users: User is being logged from a forwarded message.")
        users_sql.update_user(
            message.forward_from.id,
            message.forward_from.username,  
        )
        return

    LOGGER.info("Users: User is being logged from a standard message.")
    users_sql.update_user(message.from_user.id, message.from_user.username, chat.id, chat.title)

async def chat_checker(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    bot = context.bot 
    try:
        bot_member = await dispatcher.bot.get_chat(chat.id)
        if bot_member.permissions.can_send_messages is False: # These are only the default chat permissions
            await bot.leave_chat(chat.id)
    except BadRequest:
        pass  

def __migrate__(old_chat_id, new_chat_id):
    users_sql.migrate_chat(old_chat_id, new_chat_id)

__module_name__ = "Users"
__help__= """
• `/groups` - Get a list of all the chats that the bot is presently in.

*Dev user only*
•`[/broadcastall, /broadcastgroups, /broadcastusers] <message>` - Broadcasts a message 
"""

USER_LOG_HANDLER = MessageHandler(filters.ALL & filters.CHAT, log_user)
BROADCAST_HANDLER = CommandHandler(
    ["broadcastall", "broadcastgroups", "broadcastusers"], broadcast
)
CHAT_CHECKER_HANDLER = MessageHandler(filters.ALL & ~filters.ChatType.PRIVATE, chat_checker)
CHATLIST_HANDLER = CommandHandler("groups", chats)

dispatcher.add_handler(USER_LOG_HANDLER, USERS_GROUP)
dispatcher.add_handler(BROADCAST_HANDLER)
dispatcher.add_handler(CHATLIST_HANDLER)
dispatcher.add_handler(CHAT_CHECKER_HANDLER, CHAT_GROUP)
dispatcher.run_polling()