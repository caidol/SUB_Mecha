from telegram import Message
from datetime import datetime, timedelta

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