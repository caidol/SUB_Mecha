from typing import List

from telegram import Message
from datetime import datetime, timedelta


VALID_STARTING_QUOTES = ("'", '"', "”")

def remove_escapes(text: str) -> str:
    formatted_message = ""
    is_escaped = False

    for counter in range(len(text)):
        if is_escaped:
            formatted_message += text[counter]
            is_escaped = False
        elif text[counter] == "\\":
            is_escaped = True 
        else:
            formatted_message += text[counter]

    return formatted_message

async def remove_quotes(text: str) -> str:
    if not any(text.startswith(char) for char in VALID_STARTING_QUOTES):
        return text.split(None, 1)
    counter = 1 # ignore first char -> is a form of a quote
    while counter < len(text):
        if text[counter] == "\\":
            counter += 1 # ignore escape slashes
        elif text[counter] == text[0]:
            break 
        counter += 1
    else:
        return text.split(None, 1)
    
    # Start from 1 to avoid starting quote, and counter is exclusive so it avoids the ending
    key = remove_escapes(text[1:counter].strip())
    if not key:
        key = text[0] + text[0] # ""
    return key

async def time_formatter(message: Message, time_value: str) -> datetime:
    if any(time_value.endswith(unit) for unit in ("m", "h", "d")):
        unit = time_value[-1]
        time_length = time_value[:-1]
        if not time_length.isdigit():
            message.reply_text("Invalid time amount specified")
            return 
        
        if unit == "m":
            until_date = int(datetime.now() + int(time_length) * 60)
        elif unit == "h":
            until_date = int(datetime.now() + int(time_length) * 60 * 60)
        elif unit == "d":
            until_date = int(datetime.now() + int(time_length) * 24 * 60 * 60)
        else:
            return 
        
        return until_date
    else:
        message.reply_text(
            "Invalid time type specified. Expected <m/h/d>, but instead got: {}".format(
                time_value[-1]
            )
        )
        return