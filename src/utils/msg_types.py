from telegram import Message

from src.utils.string_handling import button_markdown_parser
from enum import IntEnum, unique 

@unique 
class SendTypes(IntEnum):
    TEXT = 0
    BUTTON_TEXT = 1
    STICKER = 2
    DOCUMENT = 3
    PHOTO = 4
    AUDIO = 5
    VOICE = 6
    VIDEO = 7

def get_welcome_type(message: Message):
    data_type = None
    content = None
    text = ""

    try:
        if message.reply_to_message:
            if message.reply_to_message.text:
                args = message.reply_to_message.text
            else:
                args = message.reply_to_message.caption
        else:
            args = message.text.split(
                None, 1,
            )  # use python's maxsplit to separate cmd and args
    except AttributeError:
        args = False

    if message.reply_to_message and message.reply_to_message.sticker:
        content = message.reply_to_message.sticker.file_id
        text = None
        data_type = SendTypes.STICKER

    elif message.reply_to_message and message.reply_to_message.document:
        content = message.reply_to_message.document.file_id
        text = message.reply_to_message.caption
        data_type = SendTypes.DOCUMENT

    elif message.reply_to_message and message.reply_to_message.photo:
        content = message.reply_to_message.photo[-1].file_id  # last elem = best quality
        text = message.reply_to_message.caption
        data_type = SendTypes.PHOTO

    elif message.reply_to_message and message.reply_to_message.audio:
        content = message.reply_to_message.audio.file_id
        text = message.reply_to_message.caption
        data_type = SendTypes.AUDIO

    elif message.reply_to_message and message.reply_to_message.voice:
        content = message.reply_to_message.voice.file_id
        text = message.reply_to_message.caption
        data_type = SendTypes.VOICE

    elif message.reply_to_message and message.reply_to_message.video:
        content = message.reply_to_message.video.file_id
        text = message.reply_to_message.caption
        data_type = SendTypes.VIDEO

    elif message.reply_to_message and message.reply_to_message.video_note:
        content = message.reply_to_message.video_note.file_id
        text = None
        data_type = SendTypes.VIDEO_NOTE

    buttons = []
    # determine what the contents of the filter are - text, image, sticker, etc
    if args:
        if message.reply_to_message:
            argument = (
                message.reply_to_message.caption if message.reply_to_message.caption else ""
            )
            offset = 0  # offset is no need since target was in reply
            entities = message.reply_to_message.parse_entities()
        else:
            argument = args[1]
            offset = len(argument) - len(
                message.text,
            )  # set correct offset relative to command + notename
            entities = message.parse_entities()
        text, buttons = button_markdown_parser(
            argument, entities=entities, offset=offset,
        )

    if not data_type:
        if text and buttons:
            data_type = SendTypes.BUTTON_TEXT
        elif text:
            data_type = SendTypes.TEXT

    return text, data_type, content, buttons