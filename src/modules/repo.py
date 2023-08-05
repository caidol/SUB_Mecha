from src import dispatcher
from telegram import Update 
from telegram.ext import CommandHandler, CallbackContext

async def repo(update: Update, context: CallbackContext):
    link = "https://github.com/caidol/SUB_Mecha"
    await update.message.reply_text(
        f"Here is the information for the repository. Please like it if possible to support the dev -> caidol:\n\n{link}"
    )

__module_name__ = "Repository"
__help__ = """
• `/repo` - Send a link to the source code of the bot.
"""

REPO_HANDLER = CommandHandler("repo", repo)

dispatcher.add_handler(REPO_HANDLER)