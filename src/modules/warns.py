import html
import re
from typing import Optional

from src import dispatcher, LOGGER, OWNER_ID, DEV_ID
from src.core.sql import warns_sql
from src.core.decorators.chat import (
    bot_is_admin,
    user_is_admin, 
    can_restrict_members,
    user_admin_check,
    user_is_admin_no_reply,
)
from src.utils.extraction import extract_text, extract_user_only, extract_user_and_reason
from src.utils.misc import split_message
from src.utils.string_handling import remove_quotes
from src.core.sql import warns_sql
from telegram import (
    Update,
    User,
    Chat,
    Message,
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ChatPermissions

)
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    filters,
    MessageHandler,
    CallbackQueryHandler,
)
from telegram.helpers import mention_html
from telegram.error import BadRequest
from telegram.constants import ParseMode, MessageLimit

WARN_HANDLER_GROUP = 9

async def warn(update: Update, context: CallbackContext,
    user: User, chat: Chat, reason: str, 
    message: Message, warner: User = None) -> str:

    user_id = user.id
    is_admin = await user_admin_check(chat, user_id)

    if is_admin:
        await message.reply_text("Sorry, I can't warn admins!")
        return 
    
    if warner:
        warner_tag = mention_html(warner.id, warner.first_name)
    else:
        warner_tag = "Automated warn filter."
    
    limit, soft_warn = warns_sql.get_warn_setting(chat.id)
    num_warns, reasons = warns_sql.warn_user(user_id, chat.id, reason)
    if num_warns >= limit: #limit has been reached or exceeded
        warns_sql.reset_warns(user_id, chat.id)
        if soft_warn: # the user will not be banned
            await chat.restrict_member(
                user_id,
                permissions=ChatPermissions(),
            )
            reply = (
                f"🔇 <b>Mute Event</b> 🔇\n"
                f"<b>•  User:</b> <code>{mention_html(user_id, user.first_name)}</code>\n"
                f"<b>•  Count:</b> <code>{num_warns}/{limit}</code>"
            )
        else: # In this case we ban the user
            await chat.ban_member(user_id)
            reply = (
                f"🚫 <b>Ban Event</b> 🚫\n"
                f"<b>•  User:</b> <code>{mention_html(user_id, user.first_name)}</code>\n"
                f"<b>•  Count:</b> <code>{num_warns}/{limit}</code>"
            )
        
        if not all(warn_reason is None for warn_reason in reasons):
            reply += f"\n\n<b>Reasons:</b>\n"
            for warn_reason in reasons:
                if warn_reason:
                    reply += f"\n- <code>{html.escape(warn_reason)}</code>"
                else:
                    reply += "\n- <code>None</code>"

        keyboard = None
        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN_BAN\n"
            f"<b>Admin:</b> {warner_tag}\n"
            f"<b>User:</b> {mention_html(user_id, user.first_name)}\n"
            f"<b>Reason:</b> {reason}\n"
            f"<b>Counts:</b> <code>{num_warns}/{limit}</code>"
        )
    else:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "Remove warn", callback_data="rm_warn({})".format(user_id),
                    ),
                ],
            ],
        )

        reply = (
            f"🚨 <b>Warn Event</b> 🚨\n"
            f"<b>•  User:</b> <code>{mention_html(user_id, user.first_name)}</code>\n"
            f"<b>•  Count:</b> <code>{num_warns}/{limit}</code>"
        )

        if reason:
            reply += f"\n<b>•  Reason:</b> <code>{html.escape(reason)}</code>"

        log_reason = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#WARN\n"
            f"<b>Admin:</b> {warner_tag}\n"
            f"<b>User:</b> {mention_html(user_id, user.first_name)}\n"
            f"<b>Reason:</b> {reason}\n"
            f"<b>Counts:</b> <code>{num_warns}/{limit}</code>"                
        )    
    
    try:
        await context.bot.send_message(
            chat.id,
            reply, reply_markup=keyboard, parse_mode=ParseMode.HTML
        )
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            message.reply_text(
                reply, reply_markup=keyboard, parse_mode=ParseMode.HTML, quote=False,
            )
        else:
            raise 
    return log_reason 


@bot_is_admin
@user_is_admin_no_reply
async def button(update: Update, context: CallbackContext) -> str:
    query: Optional[CallbackQuery] = update.callback_query
    user: Optional[User] = update.effective_user
    await query.answer()
    match = re.match(r"rm_warn\((.+?)\)", query.data)
    if match:
        user_id = match.group(1)
        chat: Optional[Chat] = update.effective_chat
        warn_remove = warns_sql.remove_warn(user_id, chat.id)
        if warn_remove:
            await update.effective_message.reply_text(
                "Warn removed by {}".format(mention_html(user.id, user.first_name)),
                parse_mode=ParseMode.HTML,
            )
            user_member = await chat.get_member(user_id)
            return (
                f"<b{html.escape(chat.title)}:</b>\n"
                f"#UNWARN\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"<b>User:</b> {mention_html(user_member.user.id, user_member.user.first_name)}"
            )
        else:
            await update.effective_message.reply_text(
                "User already has no warns.", parse_mode=ParseMode.HTML
            )

@user_is_admin
@bot_is_admin
@can_restrict_members
async def warn_user(update: Update, context: CallbackContext) -> str:
    args = context.args
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    warner: Optional[User] = update.effective_user

    user_id, reason = await extract_user_and_reason(update, message)
    warned_user = await chat.get_member(user_id)

    if message.text.startswith("/d") and message.reply_to_message:
        await message.reply_to_message.delete()
    if user_id:
        if (message.reply_to_message 
            and message.reply_to_message.from_user.id == user_id
        ):
            return await warn(
                update, context,
                message.reply_to_message.from_user,
                chat,
                reason,
                message.reply_to_message,
                warner,
            )
        else:
            return await warn(
                update, context,
                warned_user.user, 
                chat,
                reason,
                message,
                warner
            )
    else:
        await message.reply_text("I'm afraid that this user is invalid.")
    #TODO maybe write a log message to return
    return ""
        

@user_is_admin
@bot_is_admin
async def reset_warns(update: Update, context: CallbackContext) -> str:
    args = context.args 
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    user_id = await extract_user_only(update, message)

    if user_id:
        warns_sql.reset_warns(user_id, chat.id)
        await message.reply_text("Warns have been reset")
        warned_user = await chat.get_member(user_id)
        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#RESETWARNS\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
            f"<b>User:</b> {mention_html(warned_user.user.id, warned_user.user.first_name)}"
        )
    else:
        await message.reply_text("No user has been designated!")
    #TODO can add log message
    return ""

async def get_warns(update: Update, context: CallbackContext) -> None:
    message: Optional[Message] = update.effective_message 
    chat: Optional[Chat] = update.effective_chat
    user_id = await extract_user_only(update, message)
    warns_result = warns_sql.get_warns(user_id, chat.id)

    if warns_result and warns_result[0] != 0: # Ensures that the user has warns
        num_warns, reasons = warns_result
        limit, soft_warn = warns_sql.get_warn_setting(chat.id)
        
        if reasons:
            text = (
                f"🚨 This user has {num_warns}/{limit} warns 🚨. Below are the following reasons why:\n"
            )
            for reason in reasons:
                text += f"\n - {reason}"
            
            messages = split_message(text)
            for msg in messages:
                await update.message.reply_text(msg)
        else:
            await update.message.reply_text(
                f"🚨 User has {num_warns}/{limit} warns, but no reasons for any of these. 🚨"
            )
    else:
        await message.reply_text("This user does not have any warns!")

@user_is_admin
async def add_warn_filter(update: Update, context: CallbackContext) -> None:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message
    
    args = message.text.split(
        None, 1
    )

    if len(args) < 2:
        return 
    
    extracted_message = await remove_quotes(args[1]) # interprets argument as the whole phrase inside the quotes

    if len(args) >= 2:
        keyword = extracted_message[0].lower()

        try:    
            content = extracted_message[1]
        except IndexError:
            content = None

    warns_sql.add_warn_filter(chat.id, keyword, content)

    await update.effective_message.reply_text("🚨 Warn handler added for {} 🚨".format(keyword))

@user_is_admin
async def remove_warn_filter(update: Update, context: CallbackContext) -> None:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message

    args = message.text.split(
        None, 1
    )

    if len(args) < 2:
        return

    extracted_message = await remove_quotes(args[1])

    if len(extracted_message) < 1:
        return
    
    to_remove = extracted_message[0]

    chat_filters = warns_sql.get_chat_warn_triggers(chat.id)

    if not chat_filters:
        await message.reply_text("No warning filters are available to remove.")
        return 
    
    for filter in chat_filters:
        if filter[0] == to_remove:
            warns_sql.remove_warn_filter(chat.id, to_remove)
            await message.reply_text(
                f"Keyword `{to_remove}` has been successfully removed.",
                parse_mode=ParseMode.HTML,
            )
            return 
        
    await message.reply_text("Warning filter was not found in chat filters.")
    return

async def warn_list(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    all_triggers = warns_sql.get_chat_warn_triggers(chat.id)
    warning_filters_string = f"🚨 <b>Current warning filters in chat {chat.title}:</b> 🚨"

    if not all_triggers:
        await update.effective_message.reply_text("No warning filters are active here!")
        return 
    
    for keyword in all_triggers:
        current_filter = f"\n - {html.escape(keyword)}"

        if (len(warning_filters_string) + len(current_filter)) >= MessageLimit.MAX_TEXT_LENGTH:
            await update.effective_message.reply_text(warning_filters_string, parse_mode=ParseMode.HTML)
            warning_filters_string = current_filter
        else:
            warning_filters_string += f"{current_filter}"
    
    if len(warning_filters_string) <= MessageLimit.MAX_TEXT_LENGTH:
        await update.effective_message.reply_text(warning_filters_string, parse_mode=ParseMode.HTML)

async def reply_filter(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message
    user: Optional[User] = update.effective_user

    if not user: # ignore channel messages
        return 
    
    if user.id in [OWNER_ID, DEV_ID]:
        return 
    
    chat_warn_filters = warns_sql.get_chat_warn_triggers(chat.id)
    to_match = extract_text(message)
    if not to_match:
        return 
    
    if chat_warn_filters:
        for keyword in chat_warn_filters:
            pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
            if re.search(pattern, to_match, flags=re.IGNORECASE):
                user: Optional[User] = update.effective_user
                warn_filter = warns_sql.get_warn_filter(chat.id, keyword)
                return await warn(update, context, user, chat, warn_filter.reply, message)
    return ""

@user_is_admin
async def set_warn_limit(update: Update, context: CallbackContext) -> str:
    message: Optional[Message] = update.effective_message
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    args = context.args

    if args:
        if args[0].isdigit():
            if int(args[0]) < 3:
                await message.reply_text("🚨 The minimum warn limit is 3. 🚨")
            else:
                warns_sql.set_warn_limit(chat.id, warn_limit=int(args[0]))
                await message.reply_text("🚨 Updated the warn limit to {} 🚨".format(args[0]))
                return (
                    f"<b>{html.escape(chat.title)}:</b>\n"
                    f"#SET_WARN_LIMIT\n"
                    f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                    f"Set the warn limit to <code>{args[0]}</code>"
                )
        else:
            await message.reply_text("Ensure that the argument you give is a number!")
    else:
        limit, soft_warn = warns_sql.get_warn_setting(chat.id)

        await message.reply_text(
            "🚨 The current warn limit is {} 🚨\n\nPlease ensure that you specify a warn limit.".format(
                limit
            )
        )
    return ""

@user_is_admin
async def set_warn_severity(update: Update, context: CallbackContext) -> str:
    user: Optional[User] = update.effective_user
    chat: Optional[Chat] = update.effective_chat
    message: Optional[Message] = update.effective_message
    args = context.args

    if args:
        if args[0].lower() in ("on", "yes"):
            warns_sql.set_warn_severity(chat.id, False)
            await message.reply_text("🚫 Too many warns will now result in a ban! 🚫")

            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has enabled strong warns. This means users will be banned upon reaching the limit."
            )
        elif args[0].lower() in ("off", "no"):
            warns_sql.set_warn_severity(chat.id, True)
            await message.reply_text(
                "🔇 Too many warns will result in a mute. 🔇"
            )

            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has disabled strong warnings. I will now only mute users."
            )
        else:
            await message.reply_text(
                "I only understand `<on/yes/no/off>`",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        limit, soft_warn = warns_sql.get_warn_setting(chat.id)
        
        if soft_warn:
            await message.reply_text(
                "🔇 Warns are currently set to `mute` users when they exceed the limits. 🔇",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await message.reply_text(
                "🚫 Warns are currently set to `ban` users when they exceed the limits. 🚫",
                parse_mode=ParseMode.MARKDOWN,
            )
    return ""

def __stats__():
    return (
        f"• 🚨 {warns_sql.num_warns()} overall warns, across {warns_sql.num_warn_chats()} chats. 🚨\n"
        f"• 🚨 {warns_sql.num_warn_filters()} warn filters, across {warns_sql.num_warn_filter_chats()} chats. 🚨"
    )

def __migrate__(old_chat_id, new_chat_id):
    warns_sql.migrate_chat(old_chat_id, new_chat_id)

def __chat_settings__(chat_id, user_id):
    num_warn_filters = warns_sql.num_warn_chat_filters(chat_id)
    limit, soft_warn = warns_sql.get_warn_setting(chat_id)
    return (
        f"🚨 This chat has `{num_warn_filters}` warn filters. 🚨"
        f"🚨 It takes `{limit}` warns before the user gets *{'kicked' if soft_warn else 'banned'}*. 🚨"
    )

__module_name__ = "Warns"
__help__ = """
• `/warns <mention/username/id>` - Get a user's number and reason of warns.

• `/warnlist` - List of all current warning filters in a chat.

*Admins only:*

• `/warn <mention/username/id>` - Warn a user. After the specified warn limit the user will be banned from the group. Also used as reply.

• `/dwarn <mention/username/id>` - Warn a user and delete the message. After 3 warns, the user will be banned from the group. Also used as reply.

• `/resetwarn <mention/username/id>` - Reset the warns for a user. Can also be used as a reply.

• `/addwarn <warn trigger>` - Set a warning filter on a certain keyword. Sentence based warnings
can be encompassed in quotes, such as /addwarn "warn phrase" for "warn phrase" to be warned against.

• `/nowarn <keyword(s)>` - Stop a warning filter. Multiple filters must be separated by a comma.

• `/warnlimit <num>` - Set a warning limit with the num specifying how many warned messages can be sent before restriction

• `/strongwarn <on/yes/off/no>` - If set to on, exceeding the warn limit will result in a ban. Else it will mute.
"""

USER_WARNS_HANDLER = CommandHandler("warns", get_warns, filters=~filters.ChatType.PRIVATE)
LIST_WARN_HANDLER = CommandHandler(
    ["warnlist", "warnfilters"], warn_list, filters=~filters.ChatType.PRIVATE, 
)  
WARN_HANDLER = CommandHandler(
    ["warn", "dwarn"], warn_user, filters=~filters.ChatType.PRIVATE,
)
RESET_WARN_HANDLER = CommandHandler(
    ["resetwarn", "resetwarns"], reset_warns, filters=~filters.ChatType.PRIVATE,
)
ADD_WARN_HANDLER = CommandHandler("addwarn", add_warn_filter, filters=~filters.ChatType.PRIVATE)
RM_WARN_HANDLER = CommandHandler(
    ["nowarn", "stopwarn"], remove_warn_filter, filters=~filters.ChatType.PRIVATE,
)
CALLBACK_QUERY_HANDLER = CallbackQueryHandler(button, pattern=r"rm_warn")
WARN_FILTER_HANDLER = MessageHandler(
    filters.TEXT & ~filters.ChatType.PRIVATE, reply_filter,
)
WARN_LIMIT_HANDLER = CommandHandler("warnlimit", set_warn_limit, filters=~filters.ChatType.PRIVATE)
WARN_SEVERITY_HANDLER = CommandHandler(
    "strongwarn", set_warn_severity, filters=~filters.ChatType.PRIVATE,
)

dispatcher.add_handler(USER_WARNS_HANDLER)
dispatcher.add_handler(LIST_WARN_HANDLER)
dispatcher.add_handler(WARN_HANDLER)
dispatcher.add_handler(RESET_WARN_HANDLER)
dispatcher.add_handler(ADD_WARN_HANDLER)
dispatcher.add_handler(RM_WARN_HANDLER)
dispatcher.add_handler(CALLBACK_QUERY_HANDLER)
dispatcher.add_handler(WARN_FILTER_HANDLER, WARN_HANDLER_GROUP)
dispatcher.add_handler(WARN_LIMIT_HANDLER)
dispatcher.add_handler(WARN_SEVERITY_HANDLER)
