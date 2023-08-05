from typing import Optional

from telegram import Update, Message
from telegram.ext import CommandHandler, CallbackContext

from src import dispatcher
from src.utils.misc import make_carbon

async def carbon_func(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    if not message.reply_to_message:
        return await message.reply_text(
            "Reply to a text to make it carbon."
        )
    if not message.reply_to_message.text:
        return await message.reply_text(
            "Reply to a text with a message to make it carbon."
        )
    m = await message.reply_text("Preparing Carbon")
    carbon = await make_carbon(message.reply_to_message.text)
    await m.edit_text("Uploading")
    await dispatcher.bot.send_document(message.chat_id, carbon)
    await m.delete()
    carbon.close()

__module_name__ = "Carbon"
__help__ = """
• `/carbon <text> (or reply)` - Beautify your code using carbon.now.sh
"""

CARBON_HANDLER = CommandHandler("carbon", carbon_func)

dispatcher.add_handler(CARBON_HANDLER)
