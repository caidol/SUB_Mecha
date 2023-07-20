import html
import re
import asyncio

from src import LOGGER, dispatcher
from src.core.decorators.chat import bot_is_admin, user_is_admin, user_admin_check, user_is_admin_no_reply
from src.core.sql import antiflood_sql
from src.utils.string_handling import time_formatter

from telegram import Message, Chat, Update, User, ChatPermissions
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import mention_html
from telegram.constants import ParseMode

__MODULE__ = "antiflood"
__HELP__ = """
Antiflood is a system that monitors the number of messages that are sent in a row
by a particular user. Exceeding the set flood limit will allow the user to be
restricted in a particular way - which can be configured.

With my system, I set the standard limit to around 10 messages in a row.

Below are the commands:
/getflood - Get the current settings for the flood control

<b>Admin only commands below:</b>
/toggleflood - Toggle to enable or disable flood control

<b>Note: The time_value must be given when using tban or tmute.</b>
/setfloodmode [ban/kick/mute/tban/tmute] <time_value> - Action to perform when the user has exceeded the flood limit. Defaults to mute.
"""

async def check_flood(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message

    if not user: # channels are ignored as flood only applies to users
        return 
    
    # Ignore user admins
    if user_admin_check(chat, user.id):
        antiflood_sql.update_flood(chat.id, None)
        return 

    should_ban = antiflood_sql.update_flood(chat.id, user.id)
    if not should_ban:
        return 

    try:
        get_mode, get_value = antiflood_sql.get_flood_setting(chat.id)

        if get_mode == 1: # specifies a user ban
            await chat.ban_member(user.id)
            mode_tag = "banned"
        elif get_mode == 2: # specifies a user kick
            await chat.ban_member(user.id)
            asyncio.sleep(1)
            await chat.unban_member(user.id)

            if chat.type in [chat.GROUP, chat.SUPERGROUP]:
                link = (await bot.get_chat(chat.id)).invite_link
                if not link:
                    link = await bot.export_chat_invite_link(chat.id)
                text = f"You have been unbanned from {update.effective_chat.title}. Below is the invite link if you'd wish to rejoin:\n\n{link}"

                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=text,
                        disable_web_page_preview=True, 
                    )
                except Forbidden:
                    pass
            mode_tag = "kicked"
        elif get_mode == 3: # specifies a user mute
            chat.restrict_member(user.id, permissions=ChatPermissions())
            mode_tag = "muted"
        elif get_mode == 4: # specifies a temp ban
            ban_length = time_formatter(message, get_value)
            chat.ban_member(user.id, until_date=ban_length)
            mode_tag = f"banned for {get_value}"
        elif get_mode == 5: # specifies a temp mute
            mute_length = time_formatter(message, get_value)
            chat.restrict_member(
                user.id,
                until_date=mute_length,
                permissions=ChatPermissions(),
            )
            mode_tag = f"muted for {get_value}"
        await bot.send_message(
            chat_id=chat.id,
            text = f"SOUND THE ALARMS {user.first_name} IS TRYING TO FLOOD THIS SHIP:\n{mode_tag}"
        )

        return (
            "<b>{}</b"
            "\n{html.escape(chat.title)}"
            "\n<b>User:</b> {}"
            "\nFlooded the group.".format(
                mode_tag,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name))
            )
        )
    except BadRequest:
        message.reply_text(
            "I don't have the correct permissions to carry out an antiflood system. For the timebeing I will disable antiflood."
        )
        # disable antiflood
        
        return (
            "<b>{}:</b>"
            "\n#INFO"
            "\nDon't have enough permission to restrict users so automatically disabled anti-flood".format(
                chat.title,
            )
        )

#TODO need to add a flood button

@user_is_admin
async def set_flood(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message 
    args = context.args 

    if message.chat.type == "private":
        context.bot.send_message(
            "This command is meant to be used in a group, not in a PM."
        )
        return 
    chat_id = chat.id
    chat_name = message.chat.title 

    if len(args) >= 1:
        toggle_value = args[0].lower()
        if toggle_value in ["off", "no", "0"]:
            antiflood_sql.set_flood(chat_id, 0)
            message.reply_text(f"Antiflood has been disabled in {chat_name}")
        elif toggle_value.isdigit():
            limit = int(toggle_value)

            if limit <= 0:
                antiflood_sql.set_flood(chat_id, 0)
                message.reply_text(f"Antiflood has been disabled in {chat_name}")

                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nDisable antiflood.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                    )
                )
            elif limit <= 5:
                context.bot.send_message(
                    "Antiflood must either be 0 (disabled) or a number greater than 5."
                )
                return 
            else:
                antiflood_sql.set_flood(chat_id, limit)

                message.reply_text(f"Antiflood has been set to {limit} in {chat_name}")

                return (
                    "<b>{}:</b>"
                    "\n#SETFLOOD"
                    "\n<b>Admin:</b> {}"
                    "\nSet antiflood to <code>{}</code>.".format(
                        html.escape(chat_name),
                        mention_html(user.id, html.escape(user.first_name)),
                        limit,
                    )
                )
        else:
            message.reply_text("Invalid argument. Please specify either a number, \"off\" or \"no\"")
    else:
        message.reply_text(
            text="Use `/setflood number` to enable anti-flood.\nOr use `/setflood off` to disable antiflood!.",
            parse_mode=ParseMode.HTML,
        )
    return

async def getflood(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message 

    if message.chat.type == "private":
        context.bot.send_message(
            "This command is meant to be used in a group, not in a PM."
        )
        return 
    chat_id = chat.id
    chat_name = message.chat.title 

    limit = antiflood_sql.get_flood_limit(chat_id)

    if limit == 0:
        message.reply_text(
            f"I'm not enforcing any flood control in {chat_name}."
        )
    else:
        message.reply_text(
            f"I'm currently restricting members after {limit} consecutive messages in {chat_name}."
        )

@user_is_admin
async def set_flood_mode(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    args = context.args

    if message.chat.type == "private":
        context.bot.send_message(
            "This command is meant to be used in a group, not in a PM."
        )
        return 
    chat_id = chat.id
    chat_name = message.chat.title

    if args:
        if args[0].lower() == "ban":
            type_flood = "ban"
            antiflood_sql.set_flood_severity(chat.id, 1, "0")
        elif args[0].lower() == "kick":
            type_flood = "kick"
            antiflood_sql.set_flood_severity(chat.id, 2, "0")
        elif args[0].lower() == "mute":
            type_flood = "mute"
            antiflood_sql.set_flood_severity(chat.id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1: # no time specified
                context.bot.send_message(
                    """It appears that you tried to set a time ban for antiflood without specifying any time. Try `/setfloodmode tban <timevalue>`.
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return 
            type_flood= f"temp ban for {str(args[1])}"
            antiflood_sql.set_flood_severity(chat.id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1: # no time specified
                context.bot.send_message(
                    """It appears that you tried to set a time mute for antiflood without specifying any time. Try `/setfloodmode tmute <timevalue>`.
    Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            type_flood = f"temp mute for {str(args[1])}"
            antiflood_sql.set_flood_severity(chat.id, 5, str(args[1]))
        else:
            context.bot.send_message(
                "I only understand the formats <ban/kick/mute/tban/tmute>"
            )
            return

        message.reply_text(
            f"Exceeding consecutive flood limit will result in {type_flood} in {chat_name}!"
        )

        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}\n"
            "Has changed antiflood mode. User will {}.".format(
                type_flood,
                html.escape(chat.title),
                mention_html(user.id, html.escape(user.first_name)),
            )
        ) 
    else:
        get_mode, get_value = antiflood_sql.get_flood_setting(chat_id)
        if get_mode == 1:
            type_flood = "ban"
        elif get_mode == 2:
            type_flood = "kick"
        elif get_mode == 3:
            type_flood = "mute"
        elif get_mode == 4:
            type_flood = f"tban for {get_value}"
        elif get_mode == 5:
            type_flood = f"tmute for {get_value}"
        
        message.reply_text(
            f"Sending more messages than the flood limit will result in {type_flood}"
        )
    return


if __name__ == '__main__':
    GET_FLOOD_HANDLER = CommandHandler("getflood", getflood, filters=filters.ChatType.GROUP)
    FLOOD_CHECK_HANDLER = MessageHandler(
        filters.ALL & ~filters.StatusUpdate & filters.ChatType.GROUP, check_flood
    )
    SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, filters=filters.ChatType.GROUP)

    dispatcher.add_handler(GET_FLOOD_HANDLER)
    dispatcher.add_handler(FLOOD_CHECK_HANDLER)
    dispatcher.add_handler(SET_FLOOD_HANDLER)