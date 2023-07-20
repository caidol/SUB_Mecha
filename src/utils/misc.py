from typing import List

from telegram.constants import MessageLimit

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