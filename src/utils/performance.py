import speedtest # need to install this module via pip
import psutil
import time

from src import LOGGER, BOT_START_TIME, BOT_USERNAME, OWNER_USERNAME
from src.utils.misc import get_readable_time

async def test_speedtest():
    def speed_convert(size):
        power = 2**10
        zero = 0
        units = {0: "", 1: "Kb/s", 2: "Mb/s", 3: "Gb/s", 4: "Tb/s"}
        while size > power:
            size /= power
            zero += 1
        return f"{round(size, 2)} {units[zero]}"

    speed = speedtest.Speedtest()
    info = speed.get_best_server()
    download = speed.download()
    upload = speed.upload()
    return [speed_convert(download), speed_convert(upload), info]


async def sys_status():
    program_uptime = int(time.time() - BOT_START_TIME)
    cpu_usage = psutil.cpu_percent()
    mem_usage = psutil.virtual_memory().percent
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    
    stats = f"""
{BOT_USERNAME} -> run by {OWNER_USERNAME}
----------------------------------------
Stats:
    Uptime: {get_readable_time(program_uptime)}
    CPU Usage: {cpu_usage}%
    Memory Usage: {mem_usage}%
    RAM Usage: {ram_usage}%
    Disk Usage: {disk_usage}%
    """

    return stats