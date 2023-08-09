from typing import List, Dict
from math import ceil

from telegram import InlineKeyboardButton

info_wiki_pages = {
    "Admin": "https://github.com/caidol/SUB_Mecha/wiki/Admin-module",
    "AdminMisc": "https://github.com/caidol/SUB_Mecha/wiki/Admin-miscellaneous-module",
    "Antiflood": "https://github.com/caidol/SUB_Mecha/wiki/Antiflood-module",
    "BlacklistUsers": "https://github.com/caidol/SUB_Mecha/wiki/BlacklistUsers-module",
    "Blacklists": "https://github.com/caidol/SUB_Mecha/wiki/Blacklist-module",
    "Carbon": "https://github.com/caidol/SUB_Mecha/wiki/Carbon-module",
    "Dice": "https://github.com/caidol/SUB_Mecha/wiki/Dice-module",
    "Info": "https://github.com/caidol/SUB_Mecha/wiki/Info-module",
    "Pins": "https://github.com/caidol/SUB_Mecha/wiki/Pins-module",
    "Polls": "https://github.com/caidol/SUB_Mecha/wiki/Polls-module",
    "Repository": "https://github.com/caidol/SUB_Mecha/wiki/Repo-module",
    "Users": "https://github.com/caidol/SUB_Mecha/wiki/Users-module",
    "Warns": "https://github.com/caidol/SUB_Mecha/wiki/Warns-module",
    "Weather": "https://github.com/caidol/SUB_Mecha/wiki/Weather-module",
    "Welcome": "https://github.com/caidol/SUB_Mecha/wiki/Welcome-module",
}

class EqInlineKeyboardButton(InlineKeyboardButton):
    def __eq__(self, other):
        return self.text == other.text 
    
    def __lt__(self, other):
        return self.text < other.text 
    
    def __gt__(self, other):
        return self.text > other.text
    
def paginate_modules(page_n: int, module_dict: Dict, prefix, chat=None) -> List:
    if not chat:
        modules = sorted(
            [
                EqInlineKeyboardButton(
                    x.__module_name__,
                    callback_data="{}_module({})".format(
                        prefix, x.__module_name__.lower(),
                    ),
                )
                for x in module_dict.values()
            ],
        )
    else:
        modules = sorted(
            [
                EqInlineKeyboardButton(
                    x.__module_name__,
                    callback_data="{}_module({},{})".format(
                        prefix, chat, x.__module_name__.lower()
                    ),
                )
                for x in module_dict.values()
            ],
        )
    
    pairs = list(zip(modules[::3], modules[1::3], modules[2::3]))
    i = 0
    for m in pairs:
        for _ in m:
            i += 1
    if len(modules) - i == 1:
        pairs.append((modules[-1],))
    elif len(modules) - i == 2:
        pairs.append(
            (
                modules[-2],
                modules[-1],
            )
        )

    COLUMN_SIZE = 4

    max_num_pages = ceil(len(pairs) / COLUMN_SIZE)
    modulo_page = page_n % max_num_pages

    # can only have a certain amount of buttons side by side
    if len(pairs) > COLUMN_SIZE:
        pairs = pairs[modulo_page * COLUMN_SIZE : COLUMN_SIZE * (modulo_page + 1)] + [
            (
                EqInlineKeyboardButton(
                    "❮",
                    callback_data="{}_prev({})".format(prefix, modulo_page),
                ),
                EqInlineKeyboardButton(
                    "Back",
                    callback_data="{}_home({})".format(prefix, modulo_page),
                ),
                EqInlineKeyboardButton(
                    "❯",
                    callback_data="{}_next({})".format(prefix, modulo_page),
                ),
            )
        ]
    else:
        pairs = pairs[modulo_page * COLUMN_SIZE : COLUMN_SIZE * (modulo_page + 1)] + [
            (   
                EqInlineKeyboardButton(
                    "Back",
                    callback_data="{}_home({})".format(prefix, modulo_page),
                ),
            )
        ]

    return pairs

def paginate_info(page_n: int, module_dict: Dict, prefix, chat=None) -> List:
    if not chat:
        info = sorted(
            [
                EqInlineKeyboardButton(
                    x.__module_name__,
                    url=f"{info_wiki_pages[x.__module_name__]}",
                )
                for x in module_dict.values()
            ],
        )
    else:
        info = sorted(
            [
                EqInlineKeyboardButton(
                    x.__module_name__,
                    url=f"{info_wiki_pages[x.__module_name__]}",
                )
                for x in module_dict.values()
            ],
        )
    
    pairs = list(zip(info[::3], info[1::3], info[2::3]))
    i = 0
    for m in pairs:
        for _ in m:
            i += 1
    if len(info) - i == 1:
        pairs.append((info[-1],))
    elif len(info) - i == 2:
        pairs.append(
            (
                info[-2],
                info[-1],
            )
        )

    COLUMN_SIZE = 4

    max_num_pages = ceil(len(pairs) / COLUMN_SIZE)
    modulo_page = page_n % max_num_pages

    # can only have a certain amount of buttons side by side
    if len(pairs) > COLUMN_SIZE:
        pairs = pairs[modulo_page * COLUMN_SIZE : COLUMN_SIZE * (modulo_page + 1)] + [
            (
                EqInlineKeyboardButton(
                    "❮",
                    callback_data="{}_prev({})".format(prefix, modulo_page),
                ),
                EqInlineKeyboardButton(
                    "Back",
                    callback_data="{}_home({})".format(prefix, modulo_page),
                ),
                EqInlineKeyboardButton(
                    "❯",
                    callback_data="{}_next({})".format(prefix, modulo_page),
                ),
            )
        ]
    else:
        pairs = pairs[modulo_page * COLUMN_SIZE : COLUMN_SIZE * (modulo_page + 1)] + [
            (   
                EqInlineKeyboardButton(
                    "Back",
                    callback_data="{}_home({})".format(prefix, modulo_page),
                ),
            )
        ]

    return pairs