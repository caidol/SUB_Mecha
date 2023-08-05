from random import randint, choice
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from datetime import datetime, timedelta

from src import aiohttpsession as aiosession # Comment and uncomment this in order to sort out an issue
from io import BytesIO
from telegram import Chat, Message

from typing import List
from telegram import InlineKeyboardButton
from telegram.constants import MessageLimit

async def make_carbon(code):
    url = "https://carbonara.solopov.dev/api/cook"
    async with aiosession.post(url, json={"code": code}) as resp:
        image = BytesIO(await resp.read())
    image.name = "smb_carbon.png"
    return image

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]

    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)

    for x, _ in enumerate(time_list):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "

    time_list.reverse()
    ping_time += ":".join(time_list)

    return ping_time

def split_message(message: str) -> List[str]:
    if len(message) < MessageLimit.MAX_TEXT_LENGTH:
        return [message]
    
    lines = message.splitlines(True)
    small_message = ""
    result = []
    for line in lines:
        if len(small_message) + len(line) < MessageLimit.MAX_TEXT_LENGTH:
            small_message += line
        else:
            result.append(small_message),
            small_message = line 
    else:
        # Else statement at the end of the for loop, so append the leftover string
        result.append(small_message)

    return result

def build_keyboard(buttons):
    keyb = []
    for btn in buttons:
        if btn.same_line and keyb:
            keyb[-1].append(InlineKeyboardButton(btn.name, url=btn.url))
        else:
            keyb.append([InlineKeyboardButton(btn.name, url=btn.url)])

    return keyb

def revert_buttons(buttons):
    res = ""
    for btn in buttons:
        if btn.same_line:
            res += "\n[{}](buttonurl://{}:same)".format(btn.name, btn.url)
        else:
            res += "\n[{}](buttonurl://{})".format(btn.name, btn.url)
    
    return res