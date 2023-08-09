import html
import random
import time
import re
from functools import partial
from io import BytesIO
from typing import Optional

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, Chat, User, Message
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown, mention_html, mention_markdown

from src.core.sql import welcome_sql as welcome_sql
from src import dispatcher, LOGGER, OWNER_ID, DEV_ID
from src.core.decorators.chat import bot_is_admin, user_is_admin, user_is_ban_protected, is_not_blacklisted
from src.utils.misc import revert_buttons, build_keyboard
from src.utils.msg_types import get_welcome_type
from src.utils.string_handling import markdown_parser, escape_invalid_curly_brackets

from multicolorcaptcha import CaptchaGenerator

VALID_WELCOME_FORMATTERS = [
    "first",
    "last",
    "fullname",
    "username",
    "id",
    "count",
    "chatname",
    "mention",
]

ENUM_SEND_MAP = {
    welcome_sql.SendTypes.TEXT.value: dispatcher.bot.send_message,
    welcome_sql.SendTypes.BUTTON_TEXT.value: dispatcher.bot.send_message,
    welcome_sql.SendTypes.STICKER.value: dispatcher.bot.send_sticker,
    welcome_sql.SendTypes.DOCUMENT.value: dispatcher.bot.send_document,
    welcome_sql.SendTypes.PHOTO.value: dispatcher.bot.send_photo,
    welcome_sql.SendTypes.AUDIO.value: dispatcher.bot.send_audio,
    welcome_sql.SendTypes.VOICE.value: dispatcher.bot.send_voice,
    welcome_sql.SendTypes.VIDEO.value: dispatcher.bot.send_video,
}

VERIFIED_USER_WAITLIST = {}
CAPTCHA_ANS_DICT = {}

async def send(update, message, keyboard, backup_message):
    chat: Optional[Chat] = update.effective_chat 
    should_clean = welcome_sql.clean_service(chat.id)   
    reply = update.message.message_id
    
    if should_clean:
        try:
            await dispatcher.bot.delete_message(chat.id, reply)
        except BadRequest:
            pass
        reply = False 
    
    try:
        msg = await update.effective_message.reply_text(
            message, 
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            reply_to_message_id=reply,
        )
    except BadRequest as excp:
        if excp.message == "Reply message not found":
            msg = await update.effective_message.reply_text(
                message,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
        elif excp.message == "Button_url_invalid":
            msg = await update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: the current message has an invalid url "
                    "in one of its buttons. Please update."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply
            )
        elif excp.message == "Unsupported url protocol":
            msg = await update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: the current message has buttons which "
                    "use url protocols that are unsupported by"
                    "telegram. Please update."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
        elif excp.message == "Wrong url host":
            msg = await update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: the current message has some bad urls. "
                    "Please update."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.warning(message)
            LOGGER.warning(keyboard)
            LOGGER.exception("Could not parse! got invalid url host errors")
        elif excp.message == "Have no rights to send a message":
            return
        else:
            msg = await update.effective_message.reply_text(
                markdown_parser(
                    backup_message + "\nNote: An error occured when sending the "
                    "custom message. Please update."
                ),
                parse_mode=ParseMode.MARKDOWN,
                reply_to_message_id=reply,
            )
            LOGGER.exception()
    return msg

async def new_member(update: Update, context: CallbackContext):
    bot, job_queue = context.bot, context.job_queue
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message

    should_welc, cust_welcome, cust_content, welc_type = welcome_sql.get_welc_pref(chat.id)
    welc_mutes = welcome_sql.welcome_mutes(chat.id)
    
    if bool(welc_mutes):
        welc_mutes = welc_mutes.lower()

    human_checks = welcome_sql.get_human_checks(user.id, chat.id)

    new_members = update.effective_message.new_chat_members

    for new_member in new_members:
        welcome_log = None
        res = None 
        sent = None 
        should_mute = True 
        welcome_bool = True 
        media_wel = False 

        if should_welc:
            reply = update.message.message_id
            should_clean = welcome_sql.clean_service(chat.id)

            # Clean service welcome 
            if should_clean:
                try:
                    await dispatcher.bot.delete_message(chat.id, reply)
                except BadRequest:
                    pass
                reply = False 
            
            # Give the owner a special welcome
            if new_member.id == OWNER_ID:
                await update.effective_message.reply_text(
                    "EVERYONE! BOW DOWN TO THE OWNER OF THIS GROUP WHO HAS JOINED US! HOW MAY WE BE OF HUMBLE SERVICE!?",
                    reply_to_message_id=reply,
                )
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Bot Owner just joined the chat."
                )
                continue
                
            # Welcome devs
            elif new_member.id == DEV_ID:
                await update.effective_message.reply_text(
                    "Be chill! My humble developer has just joined this group!",
                    reply_to_message_id=reply,
                ) 
                welcome_log = (
                    f"{html.escape(chat.title)}\n"
                    f"#USER_JOINED\n"
                    f"Bot dev just joined the group."
                )
                continue
            
            # Welcome yourself
            elif new_member.id == bot.id:
                creator = None 
                for x in bot.get_chat_administrators(update.effective_chat.id):
                    if x.status == "creator":
                        creator = x.user
                        break 
                if creator:
                    await bot.send_message(
                        chat.id,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>\n<b>Creator:</b> <code>{}</code>".format(
                            html.escape(chat.title), chat.id, html.escape(creator)
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    await bot.send_message(
                        chat.id,
                        "#NEW_GROUP\n<b>Group name:</b> {}\n<b>ID:</b> <code>{}</code>".format(
                            html.escape(chat.title), chat.id
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                await update.effective_message.reply_text(
                    "Welcome to the group!", reply_to_message_id=reply
                )
                continue
            
            else:
                buttons = welcome_sql.get_welc_buttons(chat.id)
                keyb = build_keyboard(buttons)

                if welc_type not in (welcome_sql.SendTypes.TEXT, welcome_sql.SendTypes.BUTTON_TEXT):
                    media_wel = True 
                
                first_name = (
                    new_member.first_name or "PersonWithNoName"
                )

                if cust_welcome:
                    if cust_welcome == welcome_sql.DEFAULT_WELCOME:
                        cust_welcome = random.choice(
                            welcome_sql.DEFAULT_WELCOME_MESSAGES
                        ).format(first=escape_markdown(first_name))

                    if new_member.last_name:
                        fullname = escape_markdown(f"{first_name} {new_member.last_name}")
                    else:
                        fullname = escape_markdown(first_name)
                    
                    count = await chat.get_member_count()
                    mention = mention_markdown(new_member.id, escape_markdown(first_name))

                    if new_member.username:
                        username = "@" + escape_markdown(new_member.username)
                    else:
                        username = mention

                    valid_format = escape_invalid_curly_brackets(
                        cust_welcome, VALID_WELCOME_FORMATTERS
                    )
                    res = valid_format.format(
                        first=escape_markdown(first_name),
                        last=escape_markdown(new_member.last_name or first_name),
                        fullname=escape_markdown(fullname),
                        username=username,
                        mention=mention,
                        count=count,
                        chatname=escape_markdown(chat.title),
                        id=new_member.id,
                    )
                else:
                    res = random.choice(welcome_sql.DEFAULT_WELCOME_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                    keyb = []

                backup_message = random.choice(welcome_sql.DEFAULT_WELCOME_MESSAGES).format(
                    first=escape_markdown(first_name)
                )
                keyboard = InlineKeyboardMarkup(keyb)
        else:
            welcome_bool = False
            res = None 
            keyboard = None 
            backup_message = None 
            reply = None 

        # user exceptions from welcomemutes
        member = await chat.get_member(new_member.id) 

        user_ban_protected = await user_is_ban_protected(chat, new_member.id, member or human_checks)
        if user_ban_protected:
            should_mute = False 
        
        # Join welcome: soft mute 
        if new_member.is_bot:
            should_mute = False 
        
        if new_member.id:
            if should_mute:
                if welc_mutes == "soft":
                    LOGGER.info("WELCOME MUTES ARE SOFT SO WILL RESTRICT")
                    await chat.restrict_member(
                        new_member.id,
                        permissions=ChatPermissions(
                            can_send_messages=True,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_add_web_page_previews=False,
                        ),
                        until_date=(int(time.time() + 24 * 60 * 60)),
                    )
                    LOGGER.info("CHAT MEMBER RESTRICTED UNDER SOFT MUTE")
                if welc_mutes == "strong":
                    LOGGER.info("WELCOME MUTES ARE STRONG SO WILL HEAVILY RESTRICT")
                    welcome_bool = False
                    if not media_wel:
                        VERIFIED_USER_WAITLIST.update(
                            {
                                new_member.id: {
                                    "should_welc": should_welc,
                                    "media_wel": False,
                                    "status": False,
                                    "update": update,
                                    "res": res,
                                    "keyboard": keyboard,
                                    "backup_message": backup_message
                                }
                            }
                        )
                    else:
                        VERIFIED_USER_WAITLIST.update(
                            {
                                new_member.id: {
                                    "should_welc": should_welc,
                                    "chat_id": chat.id,
                                    "media_wel": True,
                                    "status": False,
                                    "cust_content": cust_content,
                                    "welc_type": welc_type,
                                    "res": res,
                                    "keyboard": keyboard,
                                }
                            }
                        )
                    new_join_member = f'<a href="tg://user?id={user.id}">{html.escape(new_member.first_name)}</a>'
                    check_message = await message.reply_text(
                        f"{new_join_member}, click the button below to prove you're human.\nYou have 120 seconds.",
                        reply_markup=InlineKeyboardMarkup(
                            [
                                [
                                    InlineKeyboardButton(
                                        text="Yes. I'm human.👨‍⚕️",
                                        callback_data=f"user_join_({new_member.id})"
                                    )
                                ]
                            ]
                        ),
                        parse_mode=ParseMode.HTML,
                        reply_to_message_id=reply,
                    )
                    await chat.restrict_member(
                        new_member.id,
                        permissions=ChatPermissions(
                            can_send_messages=False,
                            can_send_media_messages=False,
                            can_send_other_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_send_polls=False,
                            can_change_info=False,
                            can_add_web_page_previews=False,
                        )
                    )
                    job_queue.run_once(
                        partial(check_not_bot, new_member, chat.id, check_message.message_id),
                        120,
                        name="welcomemute"
                    )
            if welc_mutes == "captcha":
                LOGGER.info("WELCOME MUTE IS CAPTCHA")
                btn = []
                # Captcha image size number (2 -> 640x360)
                CAPTCHA_SIZE_NUM = 2

                # Create Captcha Generator object of specified size 
                generator = CaptchaGenerator(CAPTCHA_SIZE_NUM)

                # Generate a captcha image 
                captcha = generator.gen_captcha_image(difficult_level=3)
                # Get information 
                image = captcha["image"]
                characters = captcha["characters"]
                fileobj = BytesIO()
                fileobj.name = f"captcha_{new_member.id}.png"
                image.save(fp=fileobj)
                fileobj.seek(0)
                CAPTCHA_ANS_DICT[(chat.id, new_member.id)] = int(characters)
                welcome_bool = False 
                if not media_wel:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_member.id): {
                                "should_welc": should_welc,
                                "media_wel": False,
                                "status": False,
                                "update": update,
                                "res": res,
                                "keyboard": keyboard,
                                "backup_message": backup_message,
                                "captcha_correct": characters,
                            }
                        }
                    )
                else:
                    VERIFIED_USER_WAITLIST.update(
                        {
                            (chat.id, new_member.id): {
                                "should_welc": should_welc,
                                "chat_id": chat.id,
                                "status": False,
                                "media_wel": True,
                                "cust_content": cust_content,
                                "welc_type": welc_type,
                                "res": res,
                                "keyboard": keyboard,
                                "captcha_correct": characters,
                            }
                        }
                    )
                
                nums = [random.randint(1000, 9999) for i in range(7)]
                nums.append(characters)
                random.shuffle(nums)
                to_append = []

                for a in nums:
                    to_append.append(
                        InlineKeyboardButton(
                            text=str(a),
                            callback_data=f"user_captchajoin_({chat.id},{new_member.id})_({a})"
                        )
                    )
                    if len(to_append) > 2:
                        btn.append(to_append)
                        to_append = []
                if to_append:
                    btn.append(to_append)

                await message.reply_photo(
                    fileobj,
                    caption=f"Welcome [{escape_markdown(new_member.first_name)}](tg://user?id={new_member.id}). "
                    f"Click the correct button to get unmuted!",
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode=ParseMode.MARKDOWN,
                    reply_to_message_id=reply,
                )

                await chat.restrict_member(
                    new_member.id, 
                    permissions=ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_invite_users=False,
                        can_pin_messages=False,
                        can_send_polls=False,
                        can_change_info=False,
                        can_add_web_page_previews=False,
                    ),
                )
        
        if welcome_bool:
            if media_wel:
                if welc_type == welcome_sql.SendTypes.STICKER.value:
                    sent = await ENUM_SEND_MAP[welc_type](
                        chat.id,
                        cust_content,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                    )
                else:
                    sent = await ENUM_SEND_MAP[welc_type](
                        chat.id,
                        cust_content,
                        caption=res,
                        reply_markup=keyboard,
                        reply_to_message_id=reply,
                        parse_mode="markdown",
                    )
            else:
                sent = await send(update, res, keyboard, backup_message)
            prev_welc = welcome_sql.get_clean_welcome_preference(chat.id)
            if prev_welc:
                try:
                    await bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass

                if sent:
                    welcome_sql.set_clean_welcome(chat.id, sent.message_id)
            
        if welcome_log:
            return welcome_log 
        
        return (
            f"{html.escape(chat.title)}\n"
            f"#USER_JOINED\n"
            f"<b>User:</b> {mention_html(user.id, user.first_name)}\n"
            f"<b>ID:</b> <code>{user.id}</code>"
        )
    return ""

async def check_not_bot(member, chat_id, message_id, context):
    bot = context.bot
    member_dict = VERIFIED_USER_WAITLIST.pop(member.id)
    member_status = member_dict.get("status")
    if not member_status:
        try:
            await bot.unban_chat_member(chat_id, member.id)
        except:
            pass 

        try:
            await bot.edit_message_text(
                "*kicks user*\nThey can always rejoin and try.",
                chat_id=chat_id,
                message_id=message_id,
            )
        except:
            pass

async def left_member(update: Update, context: CallbackContext):
    bot = context.bot 
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user 
    should_goodbye, cust_goodbye, goodbye_type = welcome_sql.get_gdbye_pref(chat.id)

    if user.id == bot.id:
        return 
    
    if should_goodbye:
        reply = update.effective_message.message_id 
        should_clean = welcome_sql.clean_service(chat.id)

        # Clean service welcome 
        if should_clean:
            try:
                await dispatcher.bot.delete_message(chat.id, reply)
            except BadRequest:
                pass 

            reply = False 
        
        left_member = update.effective_message.left_chat_member
        if left_member:
            # Ignore bot being kicked 
            if left_member.id == bot.id:
                return 
            
            # Give the owner a special goodbye
            if left_member.id == OWNER_ID:
                await update.effective_message.reply_text(
                    "NO! OUR HERO! DON'T LEAVE US NOW!!!", reply_to_message_id=reply
                )
            
            # Give the dev a special goodbye 
            if left_member.id == DEV_ID:
                await update.effective_message.reply_text(
                    "Farewell old friend... May our paths cross once more in the desolate plains..."
                )
            
            # if media goodbye, use appropriate function for it
            if goodbye_type != welcome_sql.SendTypes.TEXT and goodbye_type != welcome_sql.SendTypes.BUTTON_TEXT:
                ENUM_SEND_MAP[goodbye_type](chat.id, cust_goodbye)
                return 
            
            first_name = (
                left_member.first_name or "PersonWithNoName"
            )

            if cust_goodbye:
                if cust_goodbye == welcome_sql.DEFAULT_GOODBYE:
                    cust_goodbye = random.choice(welcome_sql.DEFAULT_GOODBYE_MESSAGES).format(
                        first=escape_markdown(first_name)
                    )
                if left_member.last_name:
                    fullname = escape_markdown(f"{first_name} {left_member.last_name}")
                else:
                    fullname = escape_markdown(first_name)
                    
                count = await chat.get_member_count()
                mention = mention_markdown(left_member.id, escape_markdown(first_name))
                if left_member.username:
                    username = "@" + escape_markdown(left_member.username)
                else:
                    username = mention
                
                valid_format = escape_invalid_curly_brackets(
                    cust_goodbye, VALID_WELCOME_FORMATTERS
                )
                res = valid_format.format(
                    first=escape_markdown(first_name),
                    last=escape_markdown(left_member.last_name or first_name),
                    fullname=escape_markdown(fullname),
                    username=username,
                    mention=mention,
                    count=count,
                    chatname=escape_markdown(chat.title),
                    id=left_member.id,
                )
                buttons = welcome_sql.get_gdbye_buttons(chat.id)
                keyb = build_keyboard(buttons)
            else:
                res = random.choice(welcome_sql.DEFAULT_GOODBYE_MESSAGES).format(
                    first=first_name,
                )
                keyb = []
            
            keyboard = InlineKeyboardMarkup(keyb)

            sent = await send(
                update, res, keyboard, 
                random.choice(welcome_sql.DEFAULT_GOODBYE_MESSAGES).format(first=first_name),
            )

            prev_goodbye = welcome_sql.get_clean_goodbye_preference(chat.id)

            if prev_goodbye:
                try:
                    await dispatcher.bot.delete_message(chat.id, prev_goodbye)
                except BadRequest:
                    pass 

                if sent:
                    welcome_sql.set_clean_goodbye(chat.id, sent.message_id)

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def welcome(update: Update, context: CallbackContext):
    args = context.args
    chat: Optional[Chat] = update.effective_chat

    if not args or args[0].lower() == "noformat":
        noformat = True
        pref, welcome_m, cust_content, welcome_type = welcome_sql.get_welc_pref(chat.id)
        
        await update.effective_message.reply_text(
            f"This chat has its welcome setting set to: `{pref}`.\n"
            f"*The welcome message (not filling the {{}}) is:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if welcome_type == welcome_sql.SendTypes.TEXT or welcome_type == welcome_sql.SendTypes.BUTTON_TEXT:
            buttons = welcome_sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                await update.effective_message.reply_text(welcome_m)
            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                await send(update, welcome_m, keyboard, welcome_sql.DEFAULT_WELCOME)
        else:
            buttons = welcome_sql.get_welc_buttons(chat.id)
            if noformat:
                welcome_m += revert_buttons(buttons)
                await ENUM_SEND_MAP[welcome_type](chat.id, cust_content, caption=welcome_m)
            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)
                await ENUM_SEND_MAP[welcome_type](
                    chat.id,
                    cust_content,
                    caption=welcome_m,
                    reply_markup=keyboard,
                    parse_mode=ParseMode.MARKDOWN,
                    disable_web_page_preview=True,
                )
    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            welcome_sql.set_welc_preference(chat.id, True)
            await update.effective_message.reply_text(
                "Great! I will now greet members when they join."
            )
        elif args[0].lower() in ("off", "no"):
            LOGGER.info("WELCOME WILL BE DISABLED")
            welcome_sql.set_welc_preference(chat.id, False)
            await update.effective_message.reply_text(
                "Okay! I will not greet users when they join the group"
            )
        else:
            await update.effective_message.reply_text(
                "I only understand 'on/yes' or 'off/no'!"
            )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def goodbye(update: Update, context: CallbackContext):
    args = context.args
    chat: Optional[Chat] = update.effective_chat

    if not args or args[0] == "noformat":
        noformat = True
        pref, goodbye_m, goodbye_type = welcome_sql.get_gdbye_pref(chat.id)

        await update.effective_message.reply_text(
            f"This chat has its goodbye setting to: `{pref}`.\n"
            f"*The goodbye message (not filling the {{}}) is:*",
            parse_mode=ParseMode.MARKDOWN,
        )

        if goodbye_type == welcome_sql.SendTypes.BUTTON_TEXT:
            buttons = welcome_sql.get_gdbye_buttons(chat.id)
            if noformat:
                goodbye_m += revert_buttons(buttons)
                await update.effective_message.reply_text(goodbye_m)
            else:
                keyb = build_keyboard(buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                await send(update, goodbye_m, keyboard, welcome_sql.DEFAULT_GOODBYE)
        else:
            if noformat:
                await ENUM_SEND_MAP[goodbye_type](chat.id, goodbye_m)
            else:
                await ENUM_SEND_MAP[goodbye_type](
                    chat.id, goodbye_m, parse_mode=ParseMode.MARKDOWN
                )
    elif len(args) >= 1:
        if args[0].lower() in ("on", "yes"):
            welcome_sql.set_gdbye_pref(chat.id, True)
            await update.effective_message.reply_text(
                "Great! I'll say goodbye to members when they leave."
            )
        elif args[0].lower() in ("off", "no"):
            welcome_sql.set_gdbye_pref(chat.id, False)
            await update.effective_message.reply_text(
                "Okay! I won't say goodbye to members when they leave."
            )
        else:
            await update.effective_message.reply_text(
                "I only understand 'on/yes' or 'off/no'!"
            )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def set_welcome(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message
    args = context.args 

    text, data_type, content, buttons = get_welcome_type(message)

    if data_type is None:
        await message.reply_text("You didn't specify what to reply with!")
        return 

    welcome_sql.set_custom_welcome(chat.id, content, text, data_type, buttons)
    await message.reply_text("Successfully set custom welcome message!")

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#SET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}"
        f"Set the welcome message"
    )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def reset_welcome(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    welcome_sql.set_custom_welcome(chat.id, None, welcome_sql.DEFAULT_WELCOME, welcome_sql.SendTypes.TEXT)
    await update.effective_message.reply_text(
        "Successfully reset welcome message to default!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_WELCOME\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Reset the welcome message to default."
    )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def set_goodbye(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message
    args = context.args 

    if len(args) >= 1:
        text, data_type, content, buttons = get_welcome_type(message)

        if data_type is None:
            await message.reply_text("You didn't specify what to reply with!")
            return ""
        
        welcome_sql.set_custom_goodbye(chat.id, content or text, data_type, buttons)
        await message.reply_text("Successfully set custom goodbye message!")

        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#SET_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Set the goodbye message."
        )
    else:
        await update.message.reply_text(
            "You must provide the word or phrase you would like the goodbye message to have."
        )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def reset_goodbye(update: Update, context: CallbackContext) -> str:
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    welcome_sql.set_custom_goodbye(chat.id, welcome_sql.DEFAULT_GOODBYE, welcome_sql.SendTypes.TEXT)
    await update.effective_message.reply_text(
        "Successfully reset goodbye message to default!"
    )

    return (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#RESET_GOODBYE\n"
        f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
        f"Reset the goodbye message."
    )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def welcomemute(update: Update, context: CallbackContext) -> str:
    args = context.args 
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            welcome_sql.set_welcome_mutes(chat.id, False)
            await message.reply_text(
                "I will no longer mute people on joining!"
            )

            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>OFF</b>."
            )
        elif args[0].lower() in ["soft"]:
            welcome_sql.set_welcome_mutes(chat.id, "soft")
            await message.reply_text(
                "I will restrict users' permissions to send media for 24 hours."
            )

            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>SOFT</b>."
            )
        elif args[0].lower() in ["strong"]:
            welcome_sql.set_welcome_mutes(chat.id, "strong")
            await message.reply_text(
                "I will now mute people when they join until they prove they're a human.\nThey'll have 120 seconds otherwise they'll be kicked."
            )

            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>STRONG</b>."
            )
    
        elif args[0].lower() in ["captcha"]:
            welcome_sql.set_welcome_mutes(chat.id, "captcha")
            await message.reply_text(
                "I will now mute people when they join until they prove they're not a bot.\nThey have to solve a captcha to get unmuted."
            )

            return (
                f"<b>{html.escape(chat.title)}:</b>\n"
                f"#WELCOME_MUTE\n"
                f"<b>• Admin:</b> {mention_html(user.id, user.first_name)}\n"
                f"Has toggled welcome mute to <b>CAPTCHA</b>."
            )
        else:
            await message.reply_text(
                "I only understand `off`/`no`/`soft`/`strong`/`captcha`!",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        current_setting = welcome_sql.welcome_mutes(chat.id)
        if current_setting == "0":
            current_setting = "false"
        reply = (
            f"\n Current setting: `{current_setting}`."
        )
        await message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

    return ""

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def clean_welcome(update: Update, context: CallbackContext) -> str:
    args = context.args 
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    if not args:
        welcome_clean_pref = welcome_sql.get_clean_welcome_preference(chat.id)
        if welcome_clean_pref:
            await update.effective_message.reply_text(
                "I should be deleting welcome messages up to two days old."
            )
        else:
            await update.effective_message.reply_text(
                "I'm currently not deleting old welcome messages."
            )
        return ""
    
    if args[0].lower() in ("on", "yes"):
        welcome_sql.set_clean_welcome(chat.id, True)
        await update.effective_message.reply_text("I'll try to delete old welcome messages.")

        return (
            f"<b>{html.escape(chat.title)}</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean welcomes to <code>ON</code>."
        )
    elif args[0].lower() in ("off", "no"):
        welcome_sql.set_clean_welcome(chat.id, False)
        await update.effective_message.reply_text("I won't delete old welcome messages.")

        return (
            f"<b>{html.escape(chat.title)}</b>\n"
            f"#CLEAN_WELCOME\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean welcomes to <code>OFF</code>."
        )
    else:
        await update.effective_message.reply_text("I understand 'on/yes' or 'off/no' only.")
        return ""

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def clean_goodbye(update: Update, context: CallbackContext) -> str: 
    args = context.args 
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user

    if not args:
        goodbye_clean_pref = welcome_sql.get_clean_goodbye_preference(chat.id)
        if goodbye_clean_pref:
            await update.effective_message.reply_text(
                "I should be deleting goodbye messages up to two days old."
            )
        else:
            await update.effective_message.reply_text(
                "I'm currently not deleting old goodbye messages"
            )
        return ""

    if args[0].lower() in ("on", "yes"):
        welcome_sql.set_clean_goodbye(chat.id, True)
        await update.effective_message.reply_text("I'll try to delete old goodbye messages.")

        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean goodbyes to <code>ON</code>"
        )
    elif args[0].lower() in ("off", "no"):
        welcome_sql.set_clean_goodbye(chat.id, False)
        await update.effective_message.reply_text("I won't delete old goodbye messages.")

        return (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#CLEAN_GOODBYE\n"
            f"<b>Admin:</b> {mention_html(user.id, user.first_name)}\n"
            f"Has toggled clean goodbyes to <code>OFF</code>"
        )

@bot_is_admin
@user_is_admin
@is_not_blacklisted
async def cleanservice(update: Update, context: CallbackContext) -> str:
    args = context.args 
    chat: Optional[Chat] = update.effective_chat

    if len(args) >= 1:
        if args[0].lower() in ("off", "no"):
            welcome_sql.set_clean_service(chat.id, False)
            await update.effective_message.reply_text(
                "Welcome clean service is `off`",
                parse_mode=ParseMode.MARKDOWN,
            )
        elif args[0].lower() in ("on", "yes"):
            welcome_sql.set_clean_service(chat.id, True)
            await update.effective_message.reply_text(
                "Welcome clean service is `on`",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.effective_message.reply_text(
                "Usage is `on`/`yes` or `off`/`no`",
                parse_mode=ParseMode.MARKDOWN,
            )
    else:
        current_setting = welcome_sql.clean_service(chat.id)
        if current_setting:
            await update.effective_message.reply_text(
                "Current clean service setting is set to: `on`",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await update.effective_message.reply_text(
                "Current clean service setting is set to: `off`",
                parse_mode=ParseMode.MARKDOWN,
            )

async def user_button(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message
    query = update.callback_query
    bot = context.bot

    match = re.match(r"user_join_\((.+?)\)", query.data)
    join_user = int(match.group(1))

    if join_user == user.id:
        welcome_sql.set_human_checks(user.id, chat.id)
        member_dict = VERIFIED_USER_WAITLIST.pop(user.id)
        member_dict["status"] = True 
        VERIFIED_USER_WAITLIST.update({user.id: member_dict})
        await query.answer(text="Nice! You're a human, unmuted!")

        await chat.restrict_member(
            user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_invite_users=True,
                can_pin_messages=True,
                can_send_polls=True,
                can_change_info=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            ),
        )
        try:
            await dispatcher.bot.delete_message(chat.id, message.message_id)
        except BadRequest:
            pass 

        if member_dict["should_welc"]:
            await bot.send_message(
                chat.id,
                "You've proved you're a human. Welcome to the group!"
            )

            if member_dict["media_wel"]:
                if member_dict["welc_type"] == welcome_sql.SendTypes.STICKER.value:
                    sent = await ENUM_SEND_MAP[member_dict["welc_type"]](
                        member_dict["chat_id"],
                        member_dict["cust_content"],
                        reply_markup=member_dict["keyboard"],
                    )
                else:
                    sent = await ENUM_SEND_MAP[member_dict["welc_type"]](
                        member_dict["chat_id"],
                        member_dict["cust_content"],
                        caption=member_dict["res"],
                        reply_markup=member_dict["keyboard"],
                        parse_mode=ParseMode.MARKDOWN,
                    )
            else:
                sent = await send(
                    member_dict["update"],
                    member_dict["res"],
                    member_dict["keyboard"],
                    member_dict["backup_message"]
                )
            
            prev_welc = welcome_sql.get_clean_welcome_preference(chat.id)
            if prev_welc:
                try:
                    await dispatcher.bot.delete_message(chat.id, prev_welc)
                except BadRequest:
                    pass 

                if sent:
                    welcome_sql.set_clean_welcome(chat.id, sent.message_id)
    else:
        await query.answer("You're not allowed to do this!")

async def user_captcha_button(update: Update, context: CallbackContext):
    chat: Optional[Chat] = update.effective_chat
    user: Optional[User] = update.effective_user
    message: Optional[Message] = update.effective_message
    query = update.callback_query
    bot = context.bot 
    
    match = re.match(r"user_captchajoin_\((.+?),(.+?)\)_\(([0-9]{4})\)", query.data)
    join_chat = int(match.group(1))
    join_user = int(match.group(2))
    captcha_ans = int(match.group(3))
    join_usr_data = await bot.get_chat(join_user)

    if join_user == user.id:
        corr_captcha_ans = CAPTCHA_ANS_DICT.pop((join_chat, join_user))
        if corr_captcha_ans == captcha_ans:
            welcome_sql.set_human_checks(user.id, chat.id)
            member_dict = VERIFIED_USER_WAITLIST[(chat.id, user.id)]
            member_dict["status"] = True 
            await context.bot.send_message(
                chat.id,
                "Nice! You're a human. Unmuted!"
            )
            
            await chat.restrict_member(
                user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_invite_users=True,
                    can_pin_messages=True,
                    can_send_polls=True,
                    can_change_info=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                ),
            )
            try:
                await dispatcher.bot.delete_message(chat.id, message.message_id)
            except BadRequest:
                pass 

            if member_dict["should_welc"]:
                if member_dict["media_wel"]:
                    if member_dict["welc_type"] == welcome_sql.SendTypes.STICKER.value:
                        sent = await ENUM_SEND_MAP[member_dict["welc_type"]](
                            member_dict["chat_id"],
                            member_dict["cust_content"],
                            reply_markup=member_dict["keyboard"],
                        )
                    else:
                        sent = await ENUM_SEND_MAP[member_dict["welc_type"]](
                            member_dict["chat_id"],
                            member_dict["cust_content"],
                            caption=member_dict["res"],
                            reply_markup=member_dict["keyboard"],
                            parse_mode=ParseMode.MARKDOWN,
                        )
                else:
                    sent = await send(
                        member_dict["update"],
                        member_dict["res"],
                        member_dict["keyboard"],
                        member_dict["backup_message"],
                    )
                
                prev_welc = welcome_sql.get_clean_welcome_preference(chat.id)
                if prev_welc:
                    try:
                        await dispatcher.bot.delete_message(chat.id, prev_welc)
                    except BadRequest:
                        pass 
                        
                    if sent:
                        welcome_sql.set_clean_welcome(chat.id, sent.message_id)
        else:
            try:
                await dispatcher.bot.delete_message(chat.id, message.message_id)
            except BadRequest:
                pass
            kicked_message = f"""
            ❌ [{escape_markdown(join_usr_data.first_name)}](tg://user?id={join_user}) failed the captcha and was kicked.
            """
            await context.bot.send_message(
                chat.id,
                "Wrong answer."
            )
            res = await chat.unban_member(join_user)
            if res:
                await context.bot.send_message(
                    chat.id,
                    text=kicked_message,
                    parse_mode=ParseMode.MARKDOWN,
                )
    
    else:
        await context.bot.send_message(
            chat.id,
            "You're not allowed to do this!"
        )

def __migrate__(old_chat_id, new_chat_id):
    welcome_sql.migrate_chat(old_chat_id, new_chat_id)

__module_name__ = "Welcome"
__help__ = """
*Admins only:*

• `/welcome <on/off>` - Enable/disable welcome messages.

• `/welcome` - Shows current welcome settings.

• `/welcome noformat` - Shows current welcome settings, without the formatting - useful to recycle your welcome messages!

• `/goodbye` - Same usage and args as `/welcome`.

• `/setwelcome <sometext>` - Set a custom welcome message. If used replying to media, uses that media.

• `/setgoodbye <sometext>` - Set a custom goodbye message. If used replying to media, uses that media.

• `/resetwelcome` - Reset to the default welcome message.

• `/resetgoodbye` - Reset to the default goodbye message.

• `/cleanwelcome <on/off>` - On new member, try to delete the previous welcome message to avoid spamming the chat.

• `/cleangoodbye <on/off>` - On a member leaving, try to delete the previous goodbye message to avoid spamming the chat.

• `/cleanservice <on/off>` - Deletes telegrams welcome/left service messages.
"""

#TODO Look more into how welcome buttons are used

NEW_MEMBER_HANDLER = MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member)
LEFT_MEMBER_HANDLER = MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, left_member)
WELCOME_PREF_HANDLER = CommandHandler("welcome", welcome, filters=~filters.ChatType.PRIVATE)
GOODBYE_PREF_HANDLER = CommandHandler("goodbye", goodbye, filters=~filters.ChatType.PRIVATE)
SET_WELCOME = CommandHandler("setwelcome", set_welcome, filters=~filters.ChatType.PRIVATE)
SET_GOODBYE = CommandHandler("setgoodbye", set_goodbye, filters=~filters.ChatType.PRIVATE)
RESET_WELCOME = CommandHandler("resetwelcome", reset_welcome, filters=~filters.ChatType.PRIVATE)
RESET_GOODBYE = CommandHandler("resetgoodbye", reset_goodbye, filters=~filters.ChatType.PRIVATE)
WELCOME_MUTE_HANDLER = CommandHandler("welcomemute", welcomemute, filters=~filters.ChatType.PRIVATE)
CLEAN_SERVICE_HANDLER = CommandHandler(
    "cleanservice", cleanservice, filters=~filters.ChatType.PRIVATE,
)
CLEAN_WELCOME = CommandHandler("cleanwelcome", clean_welcome, filters=~filters.ChatType.PRIVATE)
CLEAN_GOODBYE = CommandHandler("cleangoodbye", clean_goodbye, filters=~filters.ChatType.PRIVATE)

BUTTON_VERIFY_HANDLER = CallbackQueryHandler(user_button, pattern=r"user_join_")


CAPTCHA_BUTTON_VERIFY_HANDLER = CallbackQueryHandler(
    user_captcha_button, pattern=r"user_captchajoin_", 
)

dispatcher.add_handler(NEW_MEMBER_HANDLER)
dispatcher.add_handler(LEFT_MEMBER_HANDLER)
dispatcher.add_handler(WELCOME_PREF_HANDLER)
dispatcher.add_handler(GOODBYE_PREF_HANDLER)
dispatcher.add_handler(SET_WELCOME)
dispatcher.add_handler(SET_GOODBYE)
dispatcher.add_handler(RESET_WELCOME)
dispatcher.add_handler(RESET_GOODBYE)
dispatcher.add_handler(WELCOME_MUTE_HANDLER)
dispatcher.add_handler(CLEAN_SERVICE_HANDLER)
dispatcher.add_handler(CLEAN_WELCOME)
dispatcher.add_handler(CLEAN_GOODBYE)
dispatcher.add_handler(BUTTON_VERIFY_HANDLER)
dispatcher.add_handler(CAPTCHA_BUTTON_VERIFY_HANDLER)