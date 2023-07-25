import html
from typing import Optional

import src.core.sql.welcome_sql as welcome_sql
from src import dispatcher, LOGGER
from src.core.decorators.chat import user_is_admin 
from src.utils.misc import generate_captcha

from telegram import (
    ChatPermissions,
    Message,
    Chat,
    User,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.ext import (
    CallbackContext,
    ConversationHandler,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters
)
from telegram.helpers import escape_markdown, mention_html, mention_markdown

CAPTCHA_RESPONSE = range(1)

@user_is_admin
async def set_captcha(update: Update, context: CallbackContext) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user 
    args = context.args 

    chat_id = chat.id 
    chat_name = chat.title
    
    if args:
        if args[0].lower() in ["off", "disable"]:
            welcome_sql.update_captcha_status(chat_id, False)
            await message.reply_text(
                "The captcha will now be disabled and not be sent to new users!"
            )

            return (
                f"<b>{html.escape(chat_name)}"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
                f"Has disabled captchas. This means new users will not be sent a captcha upon joining chat."
            )
        elif args[0].lower() in ["on", "enable"]:
            welcome_sql.update_captcha_status(chat_id, True)
            await message.reply_text(
                "The captcha will now be enabled and be sent to new users!"
            )

            return (
                f"<b>{html.escape(chat_name)}"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
                f"Has enabled captchas. This means new users will be sent a captcha upon joining chat."
            )
        else:
            await message.reply_text(
                "I only understand (on/enable/off/disable)"
            )
    else:
        captcha_status = welcome_sql.get_captcha_status(chat_id)

        if captcha_status:
            await message.reply_text(
                "The captcha is currently set to *enabled* upon new users joining chat.",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await message.reply_text(
                "The captcha is currently set to *disabled upon new users joining chat.",
                parse_mode=ParseMode.MARKDOWN, 
            )

        await context.bot.send_message(
            chat_id,
            "Please ensure that you provide an argument for enabling/disabling captcha."
        )
    return ""

async def captcha(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat 
    user: Optional[User] = update.effective_user

    chat_id = chat.id

    captcha_message = """
Below is the captcha which you will need to complete in order to verify that
you are human. Simply type out the message into the chat and then it will be 
checked. 

Note that you will be restricted from performing chat activities such as 
such as sending media and will have a number of attempts at the captcha. If all
attempts are failed then you will be subsequently banned from the group.
    """

    await context.bot.send_message(
        chat_id,
        text=captcha_message
    )

    # generate the captcha
    captcha_file, correct_answer = generate_captcha()

    # store the correct answer in user data
    context.user_data["correct_captcha_answer"] = correct_answer

    if captcha_file:
        await message.reply_photo(
            photo=captcha_file,
            caption="Generated captcha for new user."
        )
    else:
        await message.reply_text(
            "Unable to generate the captcha file."
        )
        return

    return CAPTCHA_RESPONSE

async def receive_captcha_response(update: Update, context: CallbackContext) -> None:
    pass

__module__ = "greetings"

__help__ = """

/welcomehelp - Receive help information about how welcomes work
/welcomemutehelp - Receive help information about how welcome mutes work

Admins only:
/captcha [on/enable/off/disable] - Choose whether to enable/disable captcha for user upon joining a group
/welcome [on/enable/off/disable] - Enable or disable the welcome messages
/goodbye [on/enable/off/disable] - Enable or disable the goodbye messages
/setwelcome <welcome message> - Create a welcome message for the user upon joining the chat. Otherwise it will be selected from the database.
/setgoodbye <goodbye message> - Create a goodbye message for the user upon leaving the chat. Otherwise it will be selected from the database.
"""

if __name__ == "__main__":
    SET_CAPTCHA_HANDLER = ConversationHandler(
        entry_points=[MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, captcha)],
        states = {
            CAPTCHA_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, )]
        }
    )

    dispatcher.add_handler(SET_CAPTCHA_HANDLER)