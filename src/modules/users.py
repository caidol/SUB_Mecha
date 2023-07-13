from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import src.core.sql.users_sql as sql
from src import LOGGER, OWNER_ID, dispatcher

LOGGER.info("Users: Started initialisation.")

__MODULE__ = "Users"
__HELP__= """
[/broadcastall, /broadcastgroups, /broadcastusers] - Broadcasts a message (dev only)
"""

def get_user_id(username, chat_id):
    LOGGER.info("Users: Retrieving the user id given username.")

    if username.startswith("@"):
        username = username[1:]
    
    if len(username) <= 5:
        return None

    LOGGER.info("Users: Querying sql for userid given username")
    users = sql.get_userid_by_name(username)
    

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
    message = update.effective_message
    to_send = message.text.split(None, 1)

    if len(to_send) >= 2:
        group_broadcast = False
        user_broadcast = False

        if to_send[0] == "/broadcastgroups":
            group_broadcast = True
        if to_send[0] == "/broadcastusers":
            user_broadcast = True
        if to_send[0] == "/broadcastall":
            group_broadcast = user_broadcast = True

        all_chats = sql.get_all_chats() or []
        all_users = sql.get_all_users() or []
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
            f"Broadcast message complete. \nGroups failed {failed_groups} \nFailed users {failed_users}"
        )

async def log_user(update: Update, context: CallbackContext):
    chat = update.effective_chat
    message = update.effective_message

    if message.reply_to_message:
        LOGGER.info("Users: User is being logged from a replied message.")
        sql.update_user(
            message.reply_to_message.from_user.id,
            message.reply_to_message.from_user.username,
            chat.id,
            chat.title,
        )
        return
    
    if message.forward_from:
        LOGGER.info("Users: User is being logged from a forwarded message.")
        sql.update_user(
            message.forward_from.id,
            message.forward_from.username,  
        )
        return

    LOGGER.info("Users: User is being logged from a standard message.")
    sql.update_user(message.from_user.id, message.from_user.username, chat.id, chat.title)


if __name__ == '__main__':
    LOGGER.info("User: Creating and adding handlers.")
    #sql.create_tables()

    USER_LOG_HANDLER = MessageHandler(filters.ALL & filters.CHAT, log_user)
    BROADCAST_HANDLER = CommandHandler(
        ["broadcastall", "broadcastgroups", "broadcastusers"], broadcast
    )

    dispatcher.add_handler(USER_LOG_HANDLER)
    dispatcher.add_handler(BROADCAST_HANDLER)
    dispatcher.run_polling()