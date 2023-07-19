from typing import Tuple, Optional

from telegram import Message, MessageEntity, Update
from telegram.error import BadRequest

from src import LOGGER, dispatcher
from src.modules.users import get_user_id


async def extract_user_id(update: Update, message, text: str) -> int:
    # check if the text is an integer
    LOGGER.info("DEBUGGING MESSAGES FOR ID EXTRACTION")
    def is_integer(text: str) -> bool:
        try:
            int(text)
        except ValueError:
            LOGGER.info("TEXT IS NOT AN INTEGER")
            return False
        LOGGER.info("TEXT IS AN INTEGER")
        return True
    
    text = text.strip()
    # return under the assumption that the user_id was 
    # directly typed instead of a mention of their username
    if is_integer(text): 
        return int(text)
    
    # Otherwise retrieve the message entities and check for any mentions made of that user
    print("Message: ", message)
    entities = list(message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION]))
    entity = (entities[0] if entities else None)
    
     
    if entity == None:
        return get_user_id(text, update.effective_chat.id)
    elif entity.type == MessageEntity.MENTION: 
        return get_user_id(text, update.effective_chat.id)
    elif entity.type == MessageEntity.TEXT_MENTION:
        return entity.user.id
    
    return None


async def extract_user_only(update: Update, message) -> str:
    return (await extract_user_and_reason(update, message))[0]


async def extract_user_and_reason(update: Update, message: Message) -> Tuple[Optional[int], Optional[str]]:
    LOGGER.info("DEBUGGING MESSAGES FOR EXTRACTION")
    message_args = message.text.strip().split()
    message_text = message.text

    user = None
    reason = None

    if message.reply_to_message: 
        LOGGER.info("MESSAGE HAS BEEN REPLIED TO")
        original_message = message.reply_to_message

        if not original_message.from_user: # the message was sent on behalf of the chat
            if original_message.sender_chat and original_message.sender_chat.id == message.chat.id:
                id = original_message.sender_chat.id
            else:
                return None, None
        else:
            id = original_message.from_user.id

        if not (len(message_args) < 2): # reason is given
            reason = message_text.split(None, 1)[1]

        return id, reason

    # message is not replied and no reason provided
    if len(message_args) == 2:
        LOGGER.info("LENGTH OF MESSAGE IS 2")
        user = message_text.split(None, 1)[1]
        return await extract_user_id(update, message, user), None
    
    # message is not replied and reason is provided
    if len(message_args) > 2:
        LOGGER.info("LENGTH OF MESSAGE IS GREATER THAN 2")
        user, reason = message_text.split(None, 2)[1:]
        return await extract_user_id(update, message, user), reason

    LOGGER.info("USER, REASON: ", user, reason)
    return user, reason


def extract_text(message) -> str:
    return (
        message.text
        or message.caption
        or (message.sticker.emoji if message.sticker else None)
    )