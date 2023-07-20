import html
import asyncio
import re 

from telegram import Update, ChatPermissions
from telegram.error import BadRequest, Forbidden
from telegram.ext import CommandHandler, MessageHandler, CallbackContext, filters
from telegram.helpers import mention_html
from telegram.constants import ParseMode

import src.core.sql.blacklist_sql as blacklist_sql
from src import dispatcher, LOGGER
from src.core.decorators.chat import user_is_admin, user_is_not_admin
from src.utils.extraction import extract_text
from src.utils.string_handling import time_formatter
from src.utils.typing import typing_action
from src.utils.misc import split_message

BLACKLIST_GROUP = 11

@user_is_admin
@typing_action
async def get_blacklist(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat

    if chat.type == "private":
        return 
    chat_id = chat.id
    chat_name = chat.title

    filter_list = "Current blacklisted words in <b>{}</b>:\n".format(chat_name)
    all_blacklisted = blacklist_sql.get_chat_blacklist(chat_id)

    for trigger in all_blacklisted:
        filter_list += " - <code>{}</code>\n".format(html.escape(trigger))

    split_text = split_message()
    for text in split_text:
        if filter_list == "Current blacklisted words in <b>{}</b>:\n".format(
            html.escape(chat_name)
        ): # if the message has not been appended to as no blacklisted words were found
            context.bot.send_message(
                "No blacklisted words in <b>{}</b>!".format(html.escape(chat_name)),
                parse_mode=ParseMode.HTML,
            )
            return
        
        context.bot.send_message(text=text, parse_mode=ParseMode.HTML)
        

@user_is_admin
@typing_action
async def add_blacklist(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    text = message.text.split(None, 1)
    
    if chat.type == "private":
        return 
    chat_id = chat.id
    chat_name = chat.title

    if len(text) > 1: # arguments are provided
        triggers = text[1]
        words_to_blacklist = list(
            {trigger.strip() for trigger in triggers.split(",") if trigger.strip()},
        )
        for trigger in words_to_blacklist:
            blacklist_sql.add_to_blacklist(chat_id, trigger.lower())

        if len(words_to_blacklist) == 1:
            await context.bot.send_message(
                "Added blacklist <code>{}</code> in chat <b>{}</b!".format(
                    html.escape(words_to_blacklist[0], html.escape(chat_name))
                ),
                parse_mode=ParseMode.HTML,
            )
        else:
            await context.bot.send_message(
                "Added blacklist trigger: <code>{}</code> in <b>{}</b>!".format(
                    len(words_to_blacklist), html.escape(chat_name)
                ),
                parse_mode=ParseMode.HTML,
            )
    else:
        await context.bot.send_message(
            "Tell me which words you would like to add into the blacklist."
        )

@user_is_admin
@typing_action
async def unblacklist(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    chat = update.effective_chat
    text = message.text.split(None, 1)

    
    if chat.type == "private":
        return 
    chat_id = chat.id
    chat_name = chat.title

    if len(text) > 1:
        triggers = text[1]
        words_to_unblacklist = list(
            {trigger.strip() for trigger in triggers.split(",") if trigger.strip()},
        )
        successful = 0
        for trigger in words_to_unblacklist:
            success = blacklist_sql.remove_from_blacklist(chat_id, trigger.lower())
            if success:
                successful += 1

        if len(words_to_unblacklist) == 1:
            if successful:
                await context.bot.send_message(
                    update.effective_message,
                    "Removed <code>{}</code> from blacklist in <b>{}</b>!".format(
                        html.escape(words_to_unblacklist[0]), html.escape(chat_name),
                    ),
                    parse_mode=ParseMode.HTML,
                )
            else:
                await context.bot.send_message(
                    "This is not a blacklist trigger."
                )
        elif successful == len(words_to_unblacklist):
            await context.bot.send_message(
                "Removed <code>{}</code> from blacklist in <b>{}</b>!".format(
                    successful, html.escape(chat_name)
                ),
                parse_mode=ParseMode.HTML,
            )
        elif not successful:
            await context.bot.send_message(
                "None of these triggers exist so they can't be removed."
            )
        else:
            await context.bot.send_message(
                "Removed <code>{}</code> from blacklist in <b>{}</b>!\n{} did not exist, so were not removed.".format(
                    successful, html.escape(chat_name), len(words_to_unblacklist) - successful
                ),
                parse_mode=ParseMode.HTML,
            )
    else:
        await context.bot.send_message(
            "Tell me which words you would like to be removed from the blacklist."
        )

@user_is_admin
@typing_action
async def blacklist_mode(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    args = context.args 

    if message.chat.type == "private":
        context.bot.send_message(
            "This command can only be used in a group and not in a PM."
        )
        return 
    chat_id = chat.id 
    chat_name = chat.title 

    if args:
        if args[0].lower() in ["off", "nothing", "no"]:
            set_blacklist_type = "do nothing"
            blacklist_sql.set_blacklist_severity(chat_id, 0, "0")
        elif args[0].lower() in ["del", "delete"]:
            set_blacklist_type = "delete blacklisted message"
            blacklist_sql.set_blacklist_severity(chat_id, 1, "0")
        elif args[0].lower() == "warn":
            set_blacklist_type = "warn the sender of the message"
            blacklist_sql.set_blacklist_severity(chat_id, 2, "0")
        elif args[0].lower() == "mute":
            set_blacklist_type = "mute the sender of the message"
            blacklist_sql.set_blacklist_severity(chat_id, 3, "0")
        elif args[0].lower() == "kick":
            set_blacklist_type = "kick the sender of the message"
            blacklist_sql.set_blacklist_severity(chat_id, 4, "0")
        elif args[0].lower() == "ban":
            set_blacklist_type = "ban the sender of the message"
            blacklist_sql.set_blacklist_severity(chat_id, 5, "0")
        elif args[0].lower() == "tban":
            if len(args) == 1:
                context.bot.send_message(
                    """It looks like you tried to set the time value for blacklist but you didn't specify the time - Try `/blacklistmode tban <timevalue>`

Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return 
            ban_time = time_formatter(message, args[1])
            if not ban_time:
                context.bot.send_message("""Invalid time value!
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return 
            set_blacklist_type = "temporarily ban for {}".format(args[1])
            blacklist_sql.set_blacklist_severity(chat_id, 6, str(args))
        elif args[0].lower() == "tmute":
            if len(args) == 1:
                context.bot.send_message(
                    """It looks like you tried to set the time value for blacklist but you didn't specify the time - Try `/blacklistmode tmute <timevalue>`

Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return 
            mute_time = time_formatter(message, args[1])
            if not mute_time:
                context.bot.send_message("""Invalid time value!
Examples of time values: 5m = 5 minutes, 6h = 6 hours, 3d = 3 days.""",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            set_blacklist_type = "temporarily mute for {}".format(args[1])
            blacklist_sql.set_blacklist_severity(chat_id, 7, str(args[1]))
        else:
            context.bot.send_message(
                "I only understand: off/del/warn/ban/kick/mute/tban/tmute",
            )
            return
        text = "Changed blacklist mode: `{}`!".format(set_blacklist_type)
        context.bot.send_message(text, parse_mode=ParseMode.MARKDOWN)
        return (
            "<b>{}:</b>\n"
            "<b>Admin:</b> {}"
            "Changed the blacklist mode, now it will {}".format(
                html.escape(chat_name),
                mention_html(user.id, html.escape(user.first_name)),
                set_blacklist_type,
            )
        )
    else:
        get_mode, get_value = blacklist_sql.get_blacklist_setting(chat_id)
        if get_mode == 0:
            set_blacklist_type = "do nothing"
        elif get_mode == 1:
            set_blacklist_type = "delete blacklisted message"
        elif get_mode == 2:
            set_blacklist_type = "warn the sender of the message"
        elif get_mode == 3:
            set_blacklist_type = "mute the sender of the message"
        elif get_mode == 4:
            set_blacklist_type = "kick the sender of the message"
        elif get_mode == 5:
            set_blacklist_type = "ban the sender of the message"
        elif get_mode == 6:
            set_blacklist_type = "temporarily ban for {}".format(get_value)
        elif get_mode == 7:
            set_blacklist_type = "temporarily mute for {}".format(get_value)
        else:
            context.bot.send_message(
                "Current blacklistmode: *{}*.".format(set_blacklist_type),
                parse_mode=ParseMode.MARKDOWN,
            )
    return

@user_is_admin
async def delete_blacklist(update: Update, context: CallbackContext) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    user_id = user.id
    bot = context.bot 
    to_match = extract_text(message)
    if not to_match:
        return 
    
    get_mode, get_value = blacklist_sql.get_blacklist_setting(chat.id)
    chat_filters = blacklist_sql.get_chat_blacklist(chat.id)
    for trigger in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(trigger) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            try:
                if get_mode == 0:
                    return
                elif get_mode == 1:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass
                    context.bot.send_message(
                        f"Please don't use that blacklisted word again {mention_html(user_id, html.escape(user.first_name))}."
                    )
                    return
                elif get_mode == 2:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass 
                    #TODO finish with warn 
                    return 
                elif get_mode == 3:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass 
                        
                    await chat.restrict_member(
                        user.id,
                        permissions=ChatPermissions(can_send_messages=False),
                    )

                    await context.bot.send_message(
                        f"Muted {mention_html(user_id, html.escape(user.first_name))} for using a blacklisted word.",
                        parse_mode=ParseMode.HTML,
                    )
                    return 
                elif get_mode == 4:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass 

                    await message.chat.ban_member(user_id)
                    await asyncio.sleep(1)
                    await message.chat.unban_member(user_id)

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
                    context.bot.send_message(
                        f"Kicked {user.first_name} for using a blacklisted word."
                    )

                    return
                elif get_mode == 5:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass 
                    await message.chat.ban_member(user_id)

                    context.bot.send_message(
                        f"Banned {user.first_name} for using a blacklisted word."
                    )
                    return 
                elif get_mode == 6:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass

                    bantime = time_formatter(message, get_value)
                    await chat.restrict_member(
                        user_id,
                        until_date=bantime,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    context.bot.send_message(
                        f"Banned {user.first_name} until '{get_value}' for using blacklisted word: {trigger}!",
                    )
                    return
                elif get_mode == 7:
                    try:
                        await message.delete()
                    except BadRequest:
                        pass

                    mutetime = time_formatter(message, get_value)
                    await chat.restrict_member(
                        user_id,
                        until_date=mutetime,
                        permissions=ChatPermissions(can_send_messages=False),
                    )
                    context.bot.send_message(
                        f"Muted {user.first_name} until '{get_value}' for using blacklisted word: {trigger}!",
                    )
                    return
            except BadRequest as excp:
                if excp.message != "Message to delete not found":
                    LOGGER.exception("Error while deleting blacklist message.")
            break

def __migrate__(old_chat_id, new_chat_id):
    blacklist_sql.migrate_chat(old_chat_id, new_chat_id)

def __chat_settings__(chat_id):
    blacklisted_words = blacklist_sql.get_num_blacklist_chat_filters(chat_id)
    return "There are {} blacklisted words.".format(blacklisted_words)

def __stats__():
    return "• {} blacklist triggers, across {} chats.".format(
        blacklist_sql.num_blacklist_filters(), blacklist_sql.get_num_blacklist_filter_chats()
    )

if __name__ == '__main__':
    GET_BLACKLIST_HANDLER = CommandHandler("getblacklist")
    ADD_BLACKLIST_HANDLER = CommandHandler("addblacklist", add_blacklist)
    UNBLACKLIST_HANDLER = CommandHandler("unblacklist", unblacklist)
    BLACKLISTMODE_HANDLER = CommandHandler("blacklistmode", blacklist_mode, pass_args=True)
    BLACKLIST_DELETE_HANDLER = MessageHandler(
        (filters.TEXT | filters.COMMAND | filters.Sticker | filters.PHOTO) & filters.ChatType.GROUP, 
        delete_blacklist,
        allow_edit=True
    )

    dispatcher.add_handler(GET_BLACKLIST_HANDLER)
    dispatcher.add_handler(ADD_BLACKLIST_HANDLER)
    dispatcher.add_handler(UNBLACKLIST_HANDLER)
    dispatcher.add_handler(BLACKLISTMODE_HANDLER)
    dispatcher.add_handler(BLACKLIST_DELETE_HANDLER)

    