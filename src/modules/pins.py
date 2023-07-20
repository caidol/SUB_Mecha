from telegram import Update
from telegram.ext import CallbackContext, CommandHandler, filters
from telegram.error import BadRequest
from src import LOGGER, dispatcher
from src.core.decorators.chat import bot_is_admin, user_is_admin, can_pin, can_promote

@bot_is_admin
@user_is_admin
@can_pin
async def pin(update: Update, context: CallbackContext) -> None:
    args = context.args 
    chat = update.effective_chat
    message = update.effective_message

    is_group = (chat.type != "private" and chat.type != "channel") # groups are neither private chats or channels
    previous_message = message.reply_to_message # the previous message that the pin was replied to
    
    is_silent = True
    if len(args) >= 1 and previous_message:
        is_silent = not (
            args[0].lower() == "loud"
            or args[0].lower() == "notify"
        )

    if previous_message and is_group:
        try:
            await message.chat.pin_message(
                message_id=previous_message.id, disable_notification=is_silent,
            )
            return
        except BadRequest as excp:
            LOGGER.error("Admin: A bad request occurred when trying to pin a replied message.")
            raise excp

@bot_is_admin
@user_is_admin
@can_promote
async def unpin(update: Update, context: CallbackContext) -> None:
    message = update.effective_message
    previous_message = message.reply_to_message

    try:
        await message.chat.unpin_message(
            message_id=previous_message.id,
        )
    except BadRequest as excp:
            LOGGER.error("Admin: A bad request occurred when trying to unpin a replied message.")
            raise excp
    

if __name__ == '__main__':
    PIN_HANDLER = CommandHandler("pin", pin, filters=~filters.ChatType.PRIVATE)
    UNPIN_HANDLER = CommandHandler("unpin", unpin, filters=~filters.ChatType.PRIVATE)

    dispatcher.add_handler(PIN_HANDLER)
    dispatcher.add_handler(UNPIN_HANDLER)