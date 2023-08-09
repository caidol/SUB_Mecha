from typing import Optional

from src import dispatcher
from src.utils.extraction import extract_user_only
from src.core.decorators.chat import bot_is_admin, is_not_blacklisted
from src.utils.performance import test_speedtest

from telegram import Update, Chat, Message
from telegram.ext import CallbackContext, CommandHandler, filters
from telegram.constants import ParseMode

@bot_is_admin
@is_not_blacklisted
async def get_user_info(update, context, user_id):
    chat: Optional[Chat] = update.effective_chat
    chat_member = await dispatcher.bot.get_chat_member(chat.id, user_id) 
    user = chat_member.user 

    id = user.id 
    username = user.username 
    first_name = user.first_name if user.first_name else "Deleted Account"
    last_name = user.last_name
    language_code = user.language_code
    is_premium = user.is_premium
    is_bot = user.is_bot

    payload = {
        id: {
            "user_id": id,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "language_code": language_code,
            "is_premium": is_premium,
            "is_bot": is_bot,
        }
    }
    context.user_data.update(payload)
    return True

@bot_is_admin
@is_not_blacklisted
async def get_chat_info(update, context, chat_id):
    chat = await dispatcher.bot.get_chat(chat_id)

    id = chat.id 
    title = chat.title 
    type = chat.type 
    description = chat.description
    member_count = await chat.get_member_count()
    link = chat.invite_link if chat.invite_link else "None"

    payload = {
        chat_id: {
            "chat_id": id,
            "chat_title": title,
            "chat_type": type,
            "chat_description": description,
            "chat_member_count": member_count,
            "chat_link": link
        }
    }

    context.chat_data.update(payload)

    return True

@bot_is_admin
@is_not_blacklisted
async def info(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif not message.reply_to_message and len(message.text.split()) == 1:
        user_id = message.from_user.id
    elif not message.reply_to_message and len(message.text.split()) > 1:
        user_id = await extract_user_only(update, message)

    if not user_id:
        return await message.reply_text("Unable to access the user_id of this user.")
    
    process_message = await message.reply_text("Processing...")
    
    try:
        info_retrieved = await get_user_info(update, context, user_id)
    except Exception as excp:
        await message.reply_text(str(excp))

    if info_retrieved: # information was successfully stored
        try:
            user_payload = context.user_data.get(user_id)
        except KeyError:
            await message.reply_text(
                "Unable to retrieve the full user payload information."
            )
            return 

        user_info_text = f"""<b>User info:</b>
    TYPE: {"Bot" if user_payload["is_bot"] else "Member"}
    USER ID: {user_payload["user_id"]}
    USERNAME: {user_payload["username"]}
    FIRST NAME: {user_payload["first_name"]}
    LAST NAME: {user_payload["last_name"]}
    LANGUAGE: {user_payload["language_code"]}
    PREMIUM USER: {"True" if user_payload["is_premium"] else "False"}
        """

        await process_message.edit_text(
            text=user_info_text,
            parse_mode=ParseMode.HTML,
        )
    else:
        await process_message.edit_text(
            "User information not found"
        )

@bot_is_admin
@is_not_blacklisted
async def chat_info(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message
    args = context.args

    if len(args) >= 1:
        chat_id = args[0]
    elif len(args) == 0:
        chat_id = chat.id
    else:
        await message.reply_text(
            """
If you're going to provide the argument for the chat then it must
be the chat ID and not the chat name!
            """
        )
        return 

    try:
        info_retrieved = await get_chat_info(update, context, chat_id)    
    except Exception as excp:
        await message.reply_text(str(excp))
        return 
    
    process_message = await message.reply_text("Processing...")

    if info_retrieved:
        try:
            chat_payload = context.chat_data.get(chat_id)
        except KeyError:
            await message.reply_text(
                "Unable to retrieve the full chat payload information."
            )
            return 
        
        chat_info_text = f"""<b>Chat Info:</b>
    TYPE: {chat_payload["chat_type"]}
    CHAT ID: {chat_payload["chat_id"]}
    TITLE: {chat_payload["chat_title"]}
    DESCRIPTION: {chat_payload["chat_description"]}
    MEMBER COUNT: {chat_payload["chat_member_count"]}
    LINK: {chat_payload["chat_link"]}
        """

        return await process_message.edit_text(
            text=chat_info_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        await process_message.edit_text(
            "Chat information not found"
        )

@bot_is_admin
@is_not_blacklisted
async def speedtest(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    download, upload, speed_info = await test_speedtest()

    process_message = await message.reply_text("Processing...")

    speedtest_test = f"""
*Download Speed*: `{download}`

*Upload Speed*: `{upload}`

*Speed Info*: `{speed_info}`
    """

    await process_message.edit_text(
        speedtest_test,
        parse_mode=ParseMode.MARKDOWN,
    )

__module_name__ = "Info"
__help__ = """
• `/info <mention/username/id|Optional>` - Get info about a user, provide no arguments to get your own

• `/chatinfo <chat_id|Optional>` - Get info about the current chat or chat of argument provided

• `/speedtest` - Carry out a speedtest. *NOTE: It can take some time to send.*
"""

USER_INFO_HANDLER = CommandHandler("info", info)
CHAT_INFO_HANDLER = CommandHandler("chatinfo", chat_info, filters=~filters.ChatType.PRIVATE)
SPEEDTEST_HANDLER = CommandHandler("speedtest", speedtest)
dispatcher.add_handler(USER_INFO_HANDLER)
dispatcher.add_handler(CHAT_INFO_HANDLER)
dispatcher.add_handler(SPEEDTEST_HANDLER)