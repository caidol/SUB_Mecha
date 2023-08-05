import html
import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

from src import LOGGER, dispatcher
from src.core.decorators.chat import user_is_admin, user_admin_check
from src.core.sql import antiflood_sql
from src.utils.string_handling import time_formatter

from telegram import Message, Chat, User, Update, ChatPermissions
from telegram.error import BadRequest, Forbidden
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.helpers import mention_html
from telegram.constants import ParseMode

FLOOD_GROUP = 3

async def check_flood(update: Update, context: CallbackContext) -> None:
    bot = context.bot
    user: Optional[User] = update.effective_user
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

    try:
        start_time = context.user_data["start_time"]
    except KeyError:
        start_time = time.time()
        context.user_data["start_time"] = start_time
    
    if start_time:
        end_time = time.time()

    if (end_time - start_time) >= 4:
        antiflood_sql.reset_flood(chat.id, user.id)
        context.user_data["start_time"] = time.time()

    if not user: # channels are ignored as flood only applies to users
        return 
    
    # Ignore user admins
    is_admin = await user_admin_check(chat, user.id)
    if is_admin:
        antiflood_sql.update_flood(chat.id, None)
        return 
    
    should_ban = antiflood_sql.update_flood(chat.id, user.id)
    
    if not should_ban:
        return 
    try:
        get_mode, get_value = antiflood_sql.get_flood_setting(chat.id)

        if get_mode == 1: # specifies a user ban
            await chat.ban_member(user.id)
            mode_tag = "🚫 banned 🚫"
        elif get_mode == 2: # specifies a user kick
            await chat.ban_member(user.id)
            asyncio.sleep(1)
            await chat.unban_member(user.id)

            if chat.type in [chat.GROUP, chat.SUPERGROUP]:
                link = (await bot.get_chat(chat.id)).invite_link
                if not link:
                    link = await bot.export_chat_invite_link(chat.id)
                text = f"⚠️ You have been kicked from `{update.effective_chat.title}`. ⚠️\n\n Here is the invite link if you'd wish to rejoin: {link}"

                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                        disable_web_page_preview=True, 
                    )
                except Forbidden:
                    pass
            mode_tag = "⚠️ kicked ⚠️"
        elif get_mode == 3: # specifies a user mute
            await chat.restrict_member(user.id, permissions=ChatPermissions())
            mode_tag = "🔇 muted 🔇"
        elif get_mode == 4: # specifies a temp ban
            bantime = await time_formatter(message, get_value)
            await chat.ban_member(
                user.id,
                until_date=bantime,
            )

            if get_value[-1] == "m":
                time_later = datetime.now() + timedelta(minutes=int(get_value[:-1]))
            elif get_value[-1] == "h":
                time_later = datetime.now() + timedelta(hours=int(get_value[:-1]))
            elif get_value[-1] == "d":
                time_later = datetime.now() + timedelta(days=int(get_value[:-1]))

            link = (await bot.get_chat(chat.id)).invite_link
            if not link: 
                link = (await chat.export_invite_link())
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"""🚫 You have been temporarily banned! 🚫

You will be able to rejoin the group via the invite link: {link}

The time you will be unbanned after is:\n\n `{datetime.strftime(time_later, "%d %B %Y %H:%M")}`.
                    """,
                    parse_mode=ParseMode.MARKDOWN,
                )
            except Exception in (BadRequest, Forbidden):
                pass
            mode_tag = f"⌚🚫 banned for {get_value} ⌚🚫"
        elif get_mode == 5: # specifies a temp mute
            mutetime = await time_formatter(message, get_value)
            await chat.restrict_member(
                user.id,
                until_date=mutetime,
                permissions=ChatPermissions(can_send_messages=False),
            )

            mode_tag = f"⌚🔇 muted for {get_value} ⌚🔇"
        await bot.send_message(
            chat_id=chat.id,
            text = f"🌊 SOUND THE ALARMS `{user.first_name}` IS TRYING TO FLOODING THIS GROUP: 🌊\n\n`{mode_tag}`",
            parse_mode=ParseMode.MARKDOWN,
        )

        return (
            f"<b>{mode_tag}</b"
            f"\n{html.escape(chat.title)}"
            f"\n<b>User:</b> {mention_html(user.id, html.escape(user.first_name))}"
            f"\nFlooded the group."
        )
    except BadRequest:
        await message.reply_text(
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

@user_is_admin
async def set_flood(update: Update, context: CallbackContext) -> None:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message 
    args = context.args 

    if message.chat.type == "private":
        await context.bot.send_message(
            chat_id,
            "This command is meant to be used in a group, not in a PM."
        )
        return 
    chat_id = chat.id
    chat_name = message.chat.title 

    if len(args) >= 1:
        toggle_value = args[0].lower()
        if toggle_value in ["off", "no", "0"]:
            antiflood_sql.set_flood(chat_id, 0)
            await message.reply_text(
                f"🚫🌊 Antiflood has been disabled in `{chat_name}` 🚫🌊",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif toggle_value.isdigit():
            limit = int(toggle_value)

            if limit <= 0:
                antiflood_sql.set_flood(chat_id, 0)
                await message.reply_text(f"Antiflood has been disabled in `{chat_name}`", parse_mode=ParseMode.MARKDOWN,)

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
                await context.bot.send_message(
                    chat_id,
                    "Antiflood must either be `0 (disabled)` or a number greater than `5`.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return 
            else:
                antiflood_sql.set_flood(chat_id, limit)

                await message.reply_text(
                    f"🌊 Antiflood has been set to `{limit}` in `{chat_name}`. 🌊",
                    parse_mode=ParseMode.MARKDOWN,
                )

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
            await message.reply_text("Invalid argument. Please specify either a `number, \"off\" or \"no\"`", parse_mode=ParseMode.MARKDOWN,)
    else:
        await message.reply_text(
            text="Use `/setflood number` to enable anti-flood.\nOr use `/setflood off` to disable antiflood!.",
            parse_mode=ParseMode.MARKDWON,
        )
    return

async def getflood(update: Update, context: CallbackContext) -> None:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message 

    if message.chat.type == "private":
        await context.bot.send_message(
            chat_id,
            "This command is meant to be used in a group, not in a PM."
        )
        return 
    chat_id = chat.id
    chat_name = message.chat.title 

    limit = antiflood_sql.get_flood_limit(chat_id)

    if limit == 0:
        await message.reply_text(
            f"🚫🌊 I'm not enforcing any flood control in `{chat_name}`. 🚫🌊",
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await message.reply_text(
            f"🌊 I'm currently restricting members after `{limit}` consecutive messages in `{chat_name}`. 🌊",
            parse_mode=ParseMode.MARKDOWN,
        )

@user_is_admin
async def set_flood_mode(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message
    args = context.args

    if message.chat.type == "private":
        await context.bot.send_message(
            chat_id,
            "This command is meant to be used in a group, not in a PM."
        )
        return 
    chat_id = chat.id
    chat_name = message.chat.title

    if args:
        if args[0].lower() == "ban":
            type_flood = "🚫 ban 🚫"
            antiflood_sql.set_flood_severity(chat.id, 1, "0")
        elif args[0].lower() == "kick":
            type_flood = "⚠️ kick ⚠️"
            antiflood_sql.set_flood_severity(chat.id, 2, "0")
        elif args[0].lower() == "mute":
            type_flood = "🔇 mute 🔇"
            antiflood_sql.set_flood_severity(chat.id, 3, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1: # no time specified
                await context.bot.send_message(
                    chat_id,
                    """It appears that you tried to set a time ban for antiflood without specifying any time. Try `/setfloodmode tban <time_value>`.
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return 
            type_flood= f"⌚🚫 temp ban for {str(args[1])} ⌚🚫"
            antiflood_sql.set_flood_severity(chat.id, 4, str(args[1]))
        elif args[0].lower() == "tmute":
            if len(args) == 1: # no time specified
                await context.bot.send_message(
                    chat_id,
                    """It appears that you tried to set a time mute for antiflood without specifying any time. Try `/setfloodmode tmute <time_value>`.
    Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            type_flood = f"⌚🔇 temp mute for {str(args[1])} ⌚🔇"
            antiflood_sql.set_flood_severity(chat.id, 5, str(args[1]))
        else:
            await context.bot.send_message(
                chat_id,
                "I only understand the formats `<ban/kick/mute/tban/tmute>`",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        await message.reply_text(
            f"Exceeding consecutive flood limit will result in `{type_flood}` in `{chat_name}`!",
            parse_mode=ParseMode.MARKDOWN,
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
            type_flood = "🚫 ban 🚫"
        elif get_mode == 2:
            type_flood = "⚠️ kick ⚠️"
        elif get_mode == 3:
            type_flood = "🔇 mute 🔇"
        elif get_mode == 4:
            type_flood = f"⌚🚫 tban for {get_value} ⌚🚫"
        elif get_mode == 5:
            type_flood = f"⌚🔇 tmute for {get_value} ⌚🔇"
        
        await message.reply_text(
            f"Sending more messages than the flood limit will result in `{type_flood}`",
            parse_mode=ParseMode.MARKDOWN,
        )
    return

def __migrate__(old_chat_id, new_chat_id):
    antiflood_sql.migrate_chat(old_chat_id, new_chat_id)

__module_name__ = "Antiflood"
__help__ = """
Antiflood is a system that monitors the number of messages that are sent in a row
by a particular user. Exceeding the set flood limit will allow the user to be
restricted in a particular way - which can be configured.

With my system, I set the standard limit to around 6 messages spammed in a row

Below are the commands:
• `/getflood` - Get the current settings for the flood control

*Admins Only:*
• `/setflood <on/off>` - Toggle to enable or disable flood control

*Note: The time_value must be given when using tban or tmute.*

• `/setfloodmode <ban/kick/mute/tban/tmute> <time_value|if tban/tmute>` - Action to perform when the user has exceeded the flood limit. Defaults to mute.
"""

GET_FLOOD_HANDLER = CommandHandler("getflood", getflood, filters=~filters.ChatType.PRIVATE)
FLOOD_CHECK_HANDLER = MessageHandler(
    filters.ALL & ~filters.StatusUpdate.ALL & ~filters.ChatType.PRIVATE, check_flood
)
SET_FLOOD_HANDLER = CommandHandler("setflood", set_flood, filters=~filters.ChatType.PRIVATE)
SET_FLOOD_MODE_HANDLER = CommandHandler(
    "setfloodmode", set_flood_mode, filters=~filters.ChatType.PRIVATE,
)

dispatcher.add_handler(GET_FLOOD_HANDLER)
dispatcher.add_handler(FLOOD_CHECK_HANDLER, FLOOD_GROUP)
dispatcher.add_handler(SET_FLOOD_HANDLER)
dispatcher.add_handler(SET_FLOOD_MODE_HANDLER)