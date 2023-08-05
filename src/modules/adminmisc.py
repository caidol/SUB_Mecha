import os
from typing import Optional

from src import dispatcher
from src.core.decorators.chat import user_is_admin, bot_is_admin, can_change_info

from telegram import Update, Message
from telegram.ext import filters, CallbackContext, CommandHandler
from telegram.constants import ParseMode, FileSizeLimit

@bot_is_admin
@user_is_admin
@can_change_info
async def set_chat_title(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    args = context.args

    if len(args) < 1:
        return await message.reply_text("**Usage:**\n/set_chat_title NEW NAME")
    old_title = message.chat.title
    new_title = "" 
    for arg in args:
        new_title += (arg if args.index(arg) == 0 else f" {arg}")

    await message.chat.set_title(new_title)
    await message.reply_text(
        f"📝 Successfully changed group title from `{old_title}` to `{new_title}`. 📝",
        parse_mode=ParseMode.MARKDOWN,
    )

@bot_is_admin
@user_is_admin
@can_change_info
async def set_chat_description(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    args = context.args

    if len(args) < 1:
        return await message.reply_text("**Usage:**\n/set_chat_description NEW DESCRIPTION", parse_mode=ParseMode.MARKDOWN)
    old_description = message.chat.description
    new_description = ""

    for arg in args:
        new_description += (arg if args.index(arg) == 0 else f" {arg}")

    await message.chat.set_description(new_description)
    await message.reply_text(
        f"📝 Successfully changed group description from `{old_description}` to `{new_description}`.📝",
        parse_mode=ParseMode.MARKDOWN,
    )

@bot_is_admin
@user_is_admin
@can_change_info
async def set_user_title(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    args = context.args

    if not message.reply_to_message:
        return await message.reply_text(
            "Reply to a user's message to set their admin title."
        )
    if not message.reply_to_message.from_user:
        return await message.reply_text(
            "I can't change an admin title of an unkown entity."
        )
    from_user = message.reply_to_message.from_user
    if len(args) < 1:
        return await message.reply_text(
            "**Usage:**\n/set_user_title NEW ADMINISTRATOR TITLE"
        )
    title = args[0]
    await message.chat.set_administrator_custom_title(from_user.id, title)
    await message.reply_text(
        f"🫅 Successfully Changed `{from_user.mention_html}`'s Admin Title to `{title}`. 🫅",
        parse_mode=ParseMode.MARKDOWN,
    )

@bot_is_admin
@user_is_admin
@can_change_info
async def set_chat_photo(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message

    reply = message.reply_to_message
    if not reply:
        return await message.reply_text("Reply to a photo to set it as the chat photo.")

    file = (reply.document or reply.photo)[0]
    if not file:
        return await message.reply_text(
            "Reply to a photo or document to set is as the chat photo."
        )

    if file.file_size > FileSizeLimit.FILESIZE_UPLOAD:
        return await message.reply_text("The file size is too large.")

    photo_file = await dispatcher.bot.get_file(file.file_id)
    photo = await photo_file.download_to_drive()
    await message.chat.set_photo(photo)
    await message.reply_text("📸 Successfully changed group photo. 📸")
    os.remove(photo)

__module_name__ = "AdminMisc"
__help__ = """
*Admin only:*
• `/setchattitle <new title name>` - Set the name of the group/channel 

• `/setchatdescription <new chat description>` - Set the description of the group/channel 

• `/setchatphoto (reply)` - Set the profile picture of the group/channel (not working)

• `/setadmintitle (reply)` - Change the administrator title of an admin (not working)
"""

__module_info__ = """
The Admin Misc module contains miscellaneous admin features. This essentially involves being
able to change group information (Chat Title, Chat Description, Chat Photo, User Title).

It's important that the user is an admin when running these commands. The bot must also be 
an admin and specifically one that has the capability of changing information within the chat.

[setchattitle, setchatdescription]

For the chat title and chat description, you will need to write the message that you wish to 
write after specifying the command.

[setchatphoto]

The chat photo must be a photo that is replied to inside the chat. This photo will then be 
temporarily downloaded to the server so the the file can be read and the bytes data then
sent to the bot.

[setusertitle]

The admin title must also be replied to a message. The bot will check whether the user is an
admin or not but it's important to know that the user must be an admin user for their title to 
be changed.
"""


CHAT_TITLE_HANDLER = CommandHandler("setchattitle", set_chat_title, filters=~filters.ChatType.PRIVATE)
CHAT_PHOTO_HANDLER = CommandHandler("setchatphoto", set_chat_photo, filters=~filters.ChatType.PRIVATE)
CHAT_DESCRIPTION_HANDLER = CommandHandler("setchatdescription", set_chat_description, filters=~filters.ChatType.PRIVATE)
USER_TITLE_HANDLER = CommandHandler("setusertitle", set_user_title, filters=~filters.ChatType.PRIVATE)

dispatcher.add_handler(CHAT_TITLE_HANDLER)
dispatcher.add_handler(CHAT_PHOTO_HANDLER)
dispatcher.add_handler(CHAT_DESCRIPTION_HANDLER)
dispatcher.add_handler(USER_TITLE_HANDLER)
