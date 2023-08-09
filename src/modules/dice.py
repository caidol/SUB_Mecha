import re 

from src import dispatcher, LOGGER
from src.core.decorators.chat import is_not_blacklisted
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import CommandHandler, CallbackQueryHandler, CallbackContext

LOGGER.info("Dice Module: Started initialisation.")
__module_name__ = "Dice"
__help__ = """
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
            InlineKeyboardButton(constants.DiceEmoji.BASKETBALL, callback_data=f'dice_emoji(basketball)'),
            InlineKeyboardButton(constants.DiceEmoji.BOWLING, callback_data='dice_emoji(bowling)'),
            InlineKeyboardButton(constants.DiceEmoji.DARTS, callback_data='dice_emoji(darts)')
        ],
        [
            InlineKeyboardButton(constants.DiceEmoji.DICE, callback_data='dice_emoji(dice)'),
            InlineKeyboardButton(constants.DiceEmoji.FOOTBALL, callback_data='dice_emoji(football)'),
            InlineKeyboardButton(constants.DiceEmoji.SLOT_MACHINE, callback_data='dice_emoji(slot_machine)'),
        ]
    ]

@is_not_blacklisted
async def help(update: Update, context: None) -> None:
    message_id = update.effective_message.id
    try:
        await update.message.reply_text(reply_to_message_id=message_id, text=HELP_TEXT)
        LOGGER.info("Dice Module: Successfully sent dice help information.")
    except:
        LOGGER.error("Dice Module: Unable to send dice help information.")

@is_not_blacklisted
async def choose_dice_option(update: Update, context: None) -> None:
    reply_markup = InlineKeyboardMarkup(KEYBOARD)

    try:
        await update.message.reply_text("Please choose:", reply_markup=reply_markup)
        LOGGER.info("Dice Module: Successfully sent inline keyboard for dice option.")
    except:
        LOGGER.error("Dice Module: Inline keyboard for dice option sent unsuccessfully.")

@is_not_blacklisted
async def roll_dice(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    query = update.callback_query
    await query.answer()

    if query.data == "":
        LOGGER.info("Dice Module: Callback query for rolling dice was awaited and returned a null value.")
        return

    match = re.match(r"dice_emoji\((.+?)\)", query.data)
    if match:
        value = match.group(1)

        for key, emoji in DICE_OPTIONS.items():
            if value == key:
                try:
                    await context.bot.send_dice(chat_id=chat_id, emoji=emoji)
                    LOGGER.info("Dice Module: send_dice() bot method was successfully called.")
                except:
                    LOGGER.error("Dice Module: send_dice() bot method was unsuccessfully called.")

__module_name__ = "Dice"
__help__ = """
• `/dice` - Roll a dice

• `/dicehelp` - Get information about the dice values when you roll.
"""

dispatcher.add_handler(CommandHandler("dicehelp", help))
dispatcher.add_handler(CommandHandler("dice", choose_dice_option))
dispatcher.add_handler(CallbackQueryHandler(roll_dice, pattern=r"dice_emoji"))
