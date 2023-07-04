import yaml
import sys 
import logging 
import time
import os
import re
from telegram.ext import Application 

# retrieve program path
PROGRAM_PATH = re.match(r"(.*)\/src", os.getcwd())
if PROGRAM_PATH is None:
    PROGRAM_PATH = os.getcwd()
else:
    PROGRAM_PATH = PROGRAM_PATH.group(1) # Regex pattern ensures that the path is only up to the src folder no matter the location

PROGRAM_PATH = f"{PROGRAM_PATH}/"
print("program path: ", PROGRAM_PATH)

# Enable logging
logging.basicConfig(
    format="(LOGGER) %(asctime)s [%(levelname)s] -> %(message)s", level=logging.INFO, datefmt="%I:%M:%S %p",
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)
LOGGER.info("test")

CONFIG_FILENAME = "config"

# Check python version
if sys.version_info[0] < 3 or sys.version_info[1] < 6:
    LOGGER.error("You must be using a Python version of at least 3.6! This is so that the program can support multiple features. Bot quitting.")
    quit(1)


def check_python_telegram_version():
    try:
        from telegram import __version_info__
    except ImportError:
        __version_info__ = (0, 0, 0, 0, 0) # type: ignore[assignment]

    if __version_info__ < (20, 0, 0, "alpha", 1):
        UP_TO_DATE = False
    else:
        UP_TO_DATE = True

    return UP_TO_DATE


def read_yaml_data(filename):
    if check_python_telegram_version():
        try:
            #with open(f'{PROGRAM_PATH}/{filename}.yml', 'r') as file:
            #with open('/home/ai-dan/Documents/Projects/SUB_Mecha/config.yml', 'r') as file:
            with open(f'/{PROGRAM_PATH}/{filename}.yml', 'r') as file:
                output = yaml.safe_load(file)
            #print(output)

            return output
        except yaml.YAMLError as Exception:
            raise Exception("Unable to read from config file. Ensure that the config file has no errors in it and that it is named correctly.")
    else:
        LOGGER.error("Unable to read from config file. Please update your python-telegram-bot version to 20.0.0a1 or higher.")
        quit(1)


# read YAML config file data
data = read_yaml_data(CONFIG_FILENAME)

# Below we define our constants that can be imported throughout the engine.

PROGRAM_NAME = data['name']
DESCRIPTION = data['description']
LOGO = data['logo'] # must get a logo as there's currently no default logo
REPOSITORY = data['repository']

ENV = data['env']

if ENV:
    try:
        BOT_TOKEN = ENV['BOT_TOKEN']['value']
        OWNER_ID = int(ENV['OWNER_ID']['value'])
        OWNER_USERNAME = ENV['OWNER_USERNAME']['value']
        BOT_USERNAME = ENV['BOT_USERNAME']['value']
        HEROKU_URL = ENV['HEROKU_URL']['value']
        OWM_API_TOKEN = ENV['OWM_API_TOKEN']['value']
        DATABASE_URL = ENV['DATABASE_URL']['value']
    except ValueError:
        for item in ENV:
            if ENV[item]['value'] == "" and ENV[item]['required'] == True:
                LOGGER.error(f"There is no value for {item}.")
                raise Exception(f"The required item {item} has no given value.")
else:
    LOGGER.error("There is no environment variables section in the config file.")
    raise Exception("There is no environment variables section in the config file.")

# Load the application

try:
    dispatcher = Application.builder().token(BOT_TOKEN).build()
except ValueError:
    LOGGER.error("There is no token value for the bot token that can be used to create the bot application.")
    raise Exception("Unable to create the bot application as there is no defined bot token value.")

LOAD = []
NO_LOAD = []
BOT_START_TIME = time.time()

# for debug purposes
'''
print(ENV)
print(PROGRAM_NAME)
print(DESCRIPTION)
print(LOGO)
print(REPOSITORY)
print(BOT_TOKEN)
print(OWNER_ID)
print(OWNER_USERNAME)
print(HEROKU_URL)
print(dispatcher)
'''