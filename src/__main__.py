import importlib # for dynamically importing modules
import re
from typing import Optional

from src import (
    dispatcher,
    LOGGER,
    REPOSITORY,
    BOT_NAME,
    BOT_USERNAME,
)
from src.modules import ALL_MODULES
from src.utils.performance import sys_status
from src.core.commands_menu.help_menu import paginate_modules, paginate_info

from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from telegram.constants import ChatType, ParseMode

IMPORTED_MODULES = {}
HELPABLE_MODULES = {}
MIGRATEABLE_MODULES = []
STATS = []
CHAT_SETTINGS = {}
USER_SETTINGS = {}

PM_START_TEXT = f"""
Hello, nice to meet you! My name is {BOT_NAME}

I'm a Telegram Group Management and Utility bot that can 
provide a range of useful features for you or your group.
"""

HELP_STRINGS = """
General commands:
/start -> Start the bot
/hub -> Open up the main hub of features
|
|
L-> Commands 👾 -> Contains all commands that can be run.
    Source code 🛠️ -> Redirects you to the source code of the bot.
    System stats 🖥️ -> Stats, e.g Uptime and Usage.
    Help ℹ️ -> Help information on using every feature.
    Add me to your group 👥 -> Select a group to add the bot to.
"""

HUB_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton("Commands 👾", callback_data="commands"),
            InlineKeyboardButton(
                "Source Code 🛠️", 
                url=REPOSITORY,
            ),
        ],
        [
            InlineKeyboardButton("System stats 🖥️", callback_data="sys_callback"),
            InlineKeyboardButton("Module info ℹ️", callback_data="info_callback"),
        ],
        [
            InlineKeyboardButton(
                "Add me to your group 👥", url=f"https://t.me/{BOT_USERNAME}?startgroup=new",
            ),
        ],
    ]
)

HELP_KEYBOARD = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(text="Commands ❓", url=f"https://t.me/{BOT_USERNAME}/?start=help"),
            InlineKeyboardButton(
                "Source Code 🛠️", 
                url=REPOSITORY,
            ),
        ],
        [
            InlineKeyboardButton(text="Goto Hub ⛩️", url=f"https://t.me/{BOT_USERNAME}/?start=hub"),
            InlineKeyboardButton(text="System stats 🖥️", callback_data="sys_callback"),
        ]
    ]
)

# dynamically load the modules
for module_name in ALL_MODULES:
    imported_module = importlib.import_module("src.modules." + module_name)
    if not hasattr(imported_module, "__module_name__"):
        imported_module.__module_name__ = imported_module.__name__
    
    if imported_module.__module_name__.lower() not in IMPORTED_MODULES:
        IMPORTED_MODULES[imported_module.__module_name__.lower()] = imported_module
    else:
        raise Exception("Can't have two modules with the same name! Please change one of these names.")

    if hasattr(imported_module, "__help__") and imported_module.__help__:
        HELPABLE_MODULES[imported_module.__module_name__.lower()] = imported_module
    
    # In case of the group needing to be migrated to a new chat id
    if hasattr(imported_module, "__migrate__"):
        MIGRATEABLE_MODULES.append(imported_module)

    if hasattr(imported_module, "__status__"):
        STATS.append(imported_module)

    if hasattr(imported_module, "__chat_settings__"):
        CHAT_SETTINGS[imported_module.__module_name__.lower()] = imported_module
    
    if hasattr(imported_module, "__user_settings__"):
        USER_SETTINGS[imported_module.__module_name__.lower()] = imported_module
        
async def start(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message

    # It's important to check the chat type first
    if message.chat.type != ChatType.PRIVATE:
        await message.reply_text("PM me for more details.", reply_markup=HELP_KEYBOARD)
        return
    if len(message.text.split(None, 1)) > 1:
        name = (message.text.split(None, 1)[1]).lower()
        
        if "_" in "name": # for a command list call
            module = (name.split("_", 1)[1])
            if str(module) in HELPABLE_MODULES:
                await message.reply_text(
                    f"This is the list of commands for *{HELPABLE_MODULES[name].__module_name__}*:\n" +
                    HELPABLE_MODULES[name].__help__
                )
            else:
                await message.reply_text(
                    "I couldn't find the list of commands for this module/feature."
                )
        elif name == "help":
            text, keyboard = await help_parser(message.from_user.first_name)
            await message.reply_text(
                text,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
        elif name == "hub":
            await message.reply_text(
            text=PM_START_TEXT,
            reply_markup=HUB_KEYBOARD,
            disable_web_page_preview=True,
        )
    else:
        await message.reply_text(
            text=PM_START_TEXT,
            reply_markup=HUB_KEYBOARD,
            disable_web_page_preview=True,
        )
    return

async def help_parser(name, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_modules(0, HELPABLE_MODULES, "help"))
    return (
        """
Hello {first_name}, this is the commands list for all of the features
provided by {BOT_USERNAME}. If you see a module/feature that you're interested in then
just press the button to receive a list of its commands. You can select 'back' to go back
to the hub at any point or use the 'prev' and 'next' buttons to change between the different
list of commands.
""".format(
            first_name=name,
            BOT_USERNAME=BOT_USERNAME,
        ),
        keyboard,
    )

async def info_parser(name, keyboard=None):
    if not keyboard:
        keyboard = InlineKeyboardMarkup(paginate_info(0, HELPABLE_MODULES, "info"))
    return (
        """
Hello {first_name}, this is the module info list for all the features 
provided by {BOT_USERNAME}. Click on a button for a module of your choice to be redircted
to the wiki where you can receive more detailed information about that module.
""".format(
            first_name=name,
            BOT_USERNAME=BOT_USERNAME,
        ),
        keyboard,
    )

async def modules_info_button(update: Update, context: CallbackContext):
    query = update.callback_query

    home_button_match = re.match(r"info_home\((.+?)\)", query.data)
    #module_button_match = re.match(r"info_module\((.+?)\)", query.data)
    prev_button_match = re.match(r"info_prev\((.+?)\)", query.data)
    next_button_match = re.match(r"info_next\((.+?)\)", query.data)
    #back_button_match = re.match(r"info_back", query.data)
    
    welcome_text = f"""
Hello {query.from_user.first_name}, this is the module info list for all the features 
provided by {BOT_USERNAME}. Click on a button for a module of your choice to be redircted
to the wiki where you can receive more detailed information about that module.
    """

    if home_button_match:
        await query.message.edit_text(
            text=PM_START_TEXT,
            reply_markup=HUB_KEYBOARD,
            disable_web_page_preview=True
        )
    elif prev_button_match:
        current_page = int(prev_button_match.group(1))
        await query.message.edit_text(
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_info(current_page - 1, HELPABLE_MODULES, "info")
            ),
            disable_web_page_preview=True,
        )
    elif next_button_match:
        current_page = int(next_button_match.group(1))
        await query.message.edit_text(
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_info(current_page + 1, HELPABLE_MODULES, "info")
            ),
            disable_web_page_preview=True,
        )

    return await query.answer()

async def commands_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    text, keyboard = await help_parser(query.from_user.first_name)
    
    await dispatcher.bot.send_message(
        query.message.chat_id,
        text=text,
        reply_markup=keyboard,
    )

    await query.message.delete()

async def info_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    text, keyboard = await info_parser(query.from_user.first_name)

    await dispatcher.bot.send_message(
        query.message.chat_id,
        text=text,
        reply_markup=keyboard,
    )

async def show_module_commands(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message
    if message.chat.type != ChatType.PRIVATE:
        if len(message.text.split()) >= 2:
            name = (message.text.split(None, 1)[1])
            if str(name) in HELPABLE_MODULES:
                commands_keyboard = InlineKeyboardMarkup(
                    [
                        InlineKeyboardButton(
                            text="Click here.",
                            callback_data=f"https://t.me/{BOT_USERNAME}/?start=help_{name}"
                        )
                    ],
                )
                await message.reply_text(
                    f"Click the button below to get help about {name}",
                    reply_markup=commands_keyboard
                )
            else:
                await message.reply_text("PM me for more details. Choose one of the buttons below to help redirect you or provide more information.", reply_markup=HELP_KEYBOARD) # could add a keyboard
        else:
            await message.reply_text("PM me for more details. Choose one of the buttons below to help redirect you or provide more information.", reply_markup=HELP_KEYBOARD) # could add a keyboard
    else:
        if len(message.text.split()) >= 2:
            name = (message.text.split()[1])
            if str(name) in HELPABLE_MODULES:
                text = (
                    f"This is the list of commands for *{HELPABLE_MODULES[name].__module_name__}*:\n" +
                    HELPABLE_MODULES[name].__help__
                )
                await message.reply_text(text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            else:
                text, commands_keyboard = await help_parser(update.effective_user.first_name)
                await message.reply_text(
                    text,
                    reply_markup=commands_keyboard,
                    disable_web_page_preview=True,
                )
        else:
            text, commands_keyboard = await help_parser(update.effective_user.first_name)
            await message.reply_text(
                text,
                reply_markup=commands_keyboard,
                disable_web_page_preview=True,
            )

async def commands_help_buttons(update: Update, context: CallbackContext):
    query = update.callback_query

    home_button_match = re.match(r"help_home\((.+?)\)", query.data)
    module_button_match = re.match(r"help_module\((.+?)\)", query.data)
    prev_button_match = re.match(r"help_prev\((.+?)\)", query.data)
    next_button_match = re.match(r"help_next\((.+?)\)", query.data)
    back_button_match = re.match(r"help_back", query.data)
    
    welcome_text = f"""
Hello {query.from_user.first_name}, this is the commands list for all of the features
provided by {BOT_USERNAME}. If you see a module/feature that you're interested in then
just press the button to receive a list of its commands. You can select 'back' to go back
to the hub at any point or use the 'prev' and 'next' buttons to change between the different
list of commands.

    """

    if module_button_match:
        module = (module_button_match.group(1)).replace(" ", "_")
        commands_text = (
            f"Here is the list of commands for *{HELPABLE_MODULES[module].__module_name__}*:\n"
            + HELPABLE_MODULES[module].__help__
        )

        await query.message.edit_text(
            text=commands_text,
            reply_markup = InlineKeyboardMarkup(
                [[InlineKeyboardButton("Back", callback_data="help_back")]]
            ),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True,
        )
    elif home_button_match:
        await query.message.edit_text(
            text=PM_START_TEXT,
            reply_markup=HUB_KEYBOARD,
            disable_web_page_preview=True
        )
    elif prev_button_match:
        current_page = int(prev_button_match.group(1))
        await query.message.edit_text(
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(current_page - 1, HELPABLE_MODULES, "help")
            ),
            disable_web_page_preview=True,
        )
    elif next_button_match:
        current_page = int(next_button_match.group(1))
        await query.message.edit_text(
            text=welcome_text,
            reply_markup=InlineKeyboardMarkup(
                paginate_modules(current_page + 1, HELPABLE_MODULES, "help")
            ),
            disable_web_page_preview=True,
        )
    elif back_button_match:
        text, commands_keyboard = await help_parser(update.effective_user.first_name)
        await query.message.edit_text(
            text,
            reply_markup=commands_keyboard,
            disable_web_page_preview=True,
        )

    return await query.answer()

async def stats_callback(update: Update, context: CallbackContext):
    query = update.callback_query

    text = await sys_status()
    await dispatcher.bot.answer_callback_query(query.id, text=text, show_alert=True)

def migrate_chats(update: Update, context: CallbackContext):
    message: Optional[Message] = update.effective_message

    if message.migrate_to_chat_id:
        old_chat = update.effective_chat.id 
        new_chat = message.migrate_to_chat_id
    elif message.migrate_from_chat_id:
        old_chat = message.migrate_from_chat_id
        new_chat = update.effective_chat.id 
    else:
        return 
    
    LOGGER.info("Migrating from %s, to %s", str(old_chat), str(new_chat))
    for mod in MIGRATEABLE_MODULES:
        mod.__migrate__(old_chat, new_chat)

def main():
    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", show_module_commands)
    
    commands_buttons_handler = CallbackQueryHandler(commands_help_buttons, pattern=r"help_.*")
    info_buttons_handler = CallbackQueryHandler(modules_info_button, pattern=r"info_.*")
    info_callback_handler = CallbackQueryHandler(info_callback, pattern=r"info_callback")
    commands_callback_handler = CallbackQueryHandler(commands_callback, pattern=r"commands")
    stats_callback_handler = CallbackQueryHandler(stats_callback, pattern=r"sys_callback")

    migrate_handler = MessageHandler(filters.StatusUpdate.MIGRATE, migrate_chats)

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(commands_buttons_handler)
    dispatcher.add_handler(info_callback_handler)
    dispatcher.add_handler(info_buttons_handler)
    dispatcher.add_handler(commands_callback_handler)
    dispatcher.add_handler(stats_callback_handler)
    dispatcher.add_handler(migrate_handler)

    dispatcher.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    LOGGER.info("Successfully loaded modules: " + str(ALL_MODULES))
    main()