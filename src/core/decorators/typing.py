from functools import wraps 
from telegram.constants import ChatAction

def typing_action(func):
    @wraps(func)
    def command_func(update, context, *args, **kwargs):
        context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING,
        )
        return func(update, context, *args, **kwargs)

    return command_func