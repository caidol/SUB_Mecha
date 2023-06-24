from telegram import Dice, Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent, constants
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler, InlineQueryHandler

from uuid import uuid4

from __init__ import dispatcher

_MODULE_ = "Dice"
_HELP_ = """
/dice_help - Receive more information about the dice
/dice - Roll a dice."""

# TODO refactor all the code below -> IDEA (put the dice values into the dice_help command)

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_message.id
    await update.message.reply_text("test") 
    await update.message.reply_dice(reply_to_message_id=chat_id, emoji=constants.DiceEmoji.BASKETBALL)


async def choose_dice_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    update.effective_message.id
    update.effective_chat.id
    keyboard = [
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

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Please choose:", reply_markup=reply_markup)


async def roll_dice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    chat_id = -1001890854654 # fixed for now, will change later
    
    # Callback Queries need to be answered, even if no notification to the user is needed
    await query.answer()

    try:
        if query.data == "basketball":
            await update.effective_message.reply_dice(emoji=constants.DiceEmoji.BASKETBALL)
        elif query.data == "bowling":
            await update.effective_message.reply_dice(emoji=constants.DiceEmoji.BOWLING)
        elif query.data == "darts": 
            await update.effective_message.reply_dice(emoji=constants.DiceEmoji.DARTS)
        elif query.data == "dice":
            await update.effective_message.reply_dice(emoji=constants.DiceEmoji.DICE)
        elif query.data == "football":
            await update.effective_message.reply_dice(emoji=constants.DiceEmoji.FOOTBALL)
        elif query.data == "slot_machine":
            await update.effective_message.reply_dice(emoji=constants.DiceEmoji.SLOT_MACHINE)
    except AttributeError:
        if query.data == "basketball":
            await context.bot.send_dice(chat_id=chat_id, emoji=constants.DiceEmoji.BASKETBALL)
        elif query.data == "bowling":
            await context.bot.send_dice(chat_id=chat_id, emoji=constants.DiceEmoji.BOWLING)
        elif query.data == "darts": 
            await context.bot.send_dice(chat_id=chat_id, emoji=constants.DiceEmoji.DARTS)
        elif query.data == "dice":
            await context.bot.send_dice(chat_id=chat_id, emoji=constants.DiceEmoji.DICE)
        elif query.data == "football":
            await context.bot.send_dice(chat_id=chat_id, emoji=constants.DiceEmoji.FOOTBALL)
        elif query.data == "slot_machine":
            await context.bot.send_dice(chat_id=chat_id, emoji=constants.DiceEmoji.SLOT_MACHINE)

async def dice_values(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("""
    If the emoji is '🎯', a value of 6 currently represents a bullseye, while a value of 1 indicates that the dartboard was missed. 
    
If the emoji is '🏀', a value of 4 or 5 currently score a basket, while a value of 1 to 3 indicates that the basket was missed. 
    
If the emoji is '⚽', a value of 4 to 5 currently scores a goal, while a value of 1 to 3 indicates that the goal was missed. 
    
If the emoji is '🎳', a value of 6 knocks all the pins, while a value of 1 means all the pins were missed. 
    
If the emoji is '🎰', each value corresponds to a unique combination of symbols. 

If the emoji is '🎲', the value that is rolled will correspond to the value that is on top of the dice.
    
    1-6: 🎲, 🎯, 🎳
    1-5: 🏀, ⚽
    1-64: 🎰
    """)

async def inline_queries_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the inline query. This is run when you type @<bot_username> in any chat"""
    query = update.inline_query.query

    if query == "":
        return
    
    keyboard = [
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
    
    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Roll Dice",
            input_message_content=InputTextMessageContent("Please choose:"),
            reply_markup=InlineKeyboardMarkup(keyboard)
        ),
        InlineQueryResultArticle(
            id=str(uuid4()), 
            title="Get Dice Values", 
            description="Return value conditions for each dice emoji.",
            input_message_content=InputTextMessageContent("""
    If the emoji is '🎯', a value of 6 currently represents a bullseye, while a value of 1 indicates that the dartboard was missed. 
    
If the emoji is '🏀', a value of 4 or 5 currently score a basket, while a value of 1 to 3 indicates that the basket was missed. 
    
If the emoji is '⚽', a value of 4 to 5 currently scores a goal, while a value of 1 to 3 indicates that the goal was missed. 
    
If the emoji is '🎳', a value of 6 knocks all the pins, while a value of 1 means all the pins were missed. 
    
If the emoji is '🎰', each value corresponds to a unique combination of symbols. 

If the emoji is '🎲', the value that is rolled will correspond to the value that is on top of the dice.
    
    1-6: 🎲, 🎯, 🎳
    1-5: 🏀, ⚽
    1-64: 🎰
    """),
        ),
    ]  

    await update.inline_query.answer(results)

def main() -> None:
    dispatcher.add_handler(CommandHandler("dice_help", help))
    dispatcher.add_handler(CommandHandler("dice", choose_dice_option))
    dispatcher.add_handler(CallbackQueryHandler(roll_dice))
    dispatcher.add_handler(CommandHandler("dice_values", dice_values))
    dispatcher.add_handler(InlineQueryHandler(inline_queries_handler))


if __name__ == '__main__':
    main()
