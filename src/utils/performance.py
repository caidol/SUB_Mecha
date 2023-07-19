import speedtest # need to install this module via pip
import psutil
import time

from src import (
    LOGGER, 
    BOT_START_TIME,
    BOT_USERNAME,
    OWNER_USERNAME
)

def test_speedtest():
    try:
        speed = speedtest.Speedtest()
        download = speed.download()
        upload = speed.upload()
        speed_info = speed.get_best_server()
        return [download, upload, speed_info]
    except:
        LOGGER.error("The speedtest failed to run.")
        return None


def sys_status():
    program_uptime = int(time.time() - BOT_START_TIME)
    cpu_usage = psutil.cpu_percent()
    mem_usage = psutil.virtual_memory().percent
    ram_usage = psutil.virtual_memory().percent
    disk_usage = psutil.disk_usage('/').percent
    
    stats = f"""
{BOT_USERNAME} -> run by {OWNER_USERNAME}
----------------------------------------
Stats:
    Uptime: {program_uptime}
    CPU Usage: {cpu_usage}%
    Memory Usage: {mem_usage}%
    RAM Usage: {ram_usage}%
    Disk Usage: {disk_usage}%
    """

    return stats