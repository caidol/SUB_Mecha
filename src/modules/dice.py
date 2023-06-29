from src import dispatcher
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, CallbackContext

_MODULE_ = "Dice"
_HELP_ = """
/dice_help - Receive more information about the dice.
/dice - Roll a dice.
"""

DICE_OPTIONS = {"basketball": "🏀", "bowling": "🎳", "darts": "🎯", "dice": "🎲", "football": "⚽", "slot_machine": "🎰"}

HELP_TEXT = """
If the emoji is 🎲, the value that is rolled will correspond to the value that is on top of the dice.

If the emoji is 🎯, a value of 6 currently represents a bullseye, while a value of 1 indicates that the dartboard was missed. 

If the emoji is 🎳, a value of 6 knocks all the pins, while a value of 1 means all the pins were missed. 
    
If the emoji is 🏀, a value of 4 or 5 currently score a basket, while a value of 1 to 3 indicates that the basket was missed. 
    
If the emoji is ⚽, a value of 4 to 5 currently scores a goal, while a value of 1 to 3 indicates that the goal was missed. 
    
If the emoji is 🎰, each value corresponds to a unique combination of symbols. 
    
    1-6: 🎲, 🎯, 🎳
    1-5: 🏀, ⚽
    1-64: 🎰
"""

KEYBOARD = [
        [
            InlineKeyboardButton(constants.DiceEmoji.BASKETBALL, callback_data="basketball"),
            InlineKeyboardButton(constants.DiceEmoji.BOWLING, callback_data="bowling"),
            InlineKeyboardButton(constants.DiceEmoji.DARTS, callback_data="darts")
        ],
        [
            InlineKeyboardButton(constants.DiceEmoji.DICE, callback_data="dice"),
            InlineKeyboardButton(constants.DiceEmoji.FOOTBALL, callback_data="football"),
            InlineKeyboardButton(constants.DiceEmoji.SLOT_MACHINE, callback_data="slot_machine"),
        ]
    ]


async def help(update: Update, context: None) -> None:
    message_id = update.effective_message.id
    await update.message.reply_text(reply_to_message_id=message_id, text=HELP_TEXT)


async def choose_dice_option(update: Update, context: None) -> None:
    reply_markup = InlineKeyboardMarkup(KEYBOARD)

    await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def roll_dice(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    query = update.callback_query
    await query.answer()

    if query.data == "":
        return

    for key, emoji in DICE_OPTIONS.items():
        if query.data == key:
            await context.bot.send_dice(chat_id=chat_id, emoji=emoji)

def main() -> None:
    dispatcher.add_handler(CommandHandler("dice_help", help))
    dispatcher.add_handler(CommandHandler("dice", choose_dice_option))
    dispatcher.add_handler(CallbackQueryHandler(roll_dice))
    #dispatcher.run_polling()


if __name__ == '__main__':
    main()
