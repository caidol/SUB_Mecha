from telegram import Bot, Update, BotCommand, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from __init__ import dispatcher, BOT_TOKEN, LOGGER

class Menu(): # A menu can be thought of as a list of commands
    def __init__(self, token, commandNames, commandDescriptions):
        self.token = token
        self.commandNames = commandNames
        self.commandDescriptions = commandDescriptions
    
    def initialise_bot(self, token):
        try:
            bot = Bot(self.token) # initialise bot with token
            if bot:
                return True
            else:
                return False
        except:
            pass # work on except handler later

    def read_from_config(self, config_file, filetypes):
        name, filetype = config_file.split('.')
        menu_params = {}
        #print(name, filetype)

        if filetype in filetypes:
            if filetype in ['yaml', 'yml']:
                import pyyaml
                with open(config_file, 'r') as file:
                    data = yaml.safe_load(file)

                    if data:
                        LOGGER.info("YAML Data loaded in successfully.")
                    else:
                        LOGGER.warning("YAML data loaded in unsuccessfully.")
                print("YAML DATA: ", data)

                commands, descriptions = data['commands'], data['descriptions']
                print("commands dict: ", commands)
                print("descriptions dict", descriptions)

                for command_key, command_value in commands.items():
                    for description_key, description_value in descriptions.items():
                        if command_key == description_key:
                            corresponding_description = description_value
                            exists = True

                    if exists: # both have same keys
                        if command_value[0] != "/":
                            menu_params["/"+command_value] = corresponding_description
                        else:
                            menu_params[command_value] = corresponding_description
                        LOGGER.info("Set menu parameters successfully")
                    else:
                        LOGGER.error("There is no command and description values with the same key")
            
            elif filetype == 'json':
                import json
                with open(config_file, 'r') as file:
                    data = json.load(file)

                    if data:
                        LOGGER.info("JSON Data loaded in successfully.")
                    else:
                        LOGGER.warning("JSON data loaded in unsuccessfully.")
                print("JSON DATA: ", data)

                commands, descriptions = data['commands'], data['descriptions']
                print("commands dict: ", commands)
                print("descriptions dict", descriptions)

                for command_key, command_value in commands.items():
                    for description_key, description_value in descriptions.items():
                        if command_key == description_key:
                            corresponding_description = description_value
                            exists = True

                    if exists: # both have same keys
                        if command_value[0] != "/":
                            menu_params["/"+command_value] = corresponding_description
                        else:
                            menu_params[command_value] = corresponding_description
                        LOGGER.info("Set menu parameters successfully")
                    else:
                        LOGGER.error("There is no command and description values with the same key")
            
        return menu_params

    def create_menu(self):
        # read menu from config
        menu = None

    def show_menu(self):
        menu_list = """ """ # Empty triple quoted string

        for i in self.commandNames:
            for j in self.commandDescriptions:
                menu_list += f"{i}: {j}\n"

        return menu_list

# TODO work on adding or removing the command

    def add_command(self, commandName, commandDescription):
        # perform checks on a valid input

        self.commandNames += commandName
        self.commandDescriptions += commandDescription
    
    def remove_command(self, commandName, commandDescription):
        # perform checks on a valid input

        for i in self.commandNames:
            for j in self.commandDescriptions:
                if i == commandName and j == commandDescription:
                    self.commandNames.remove(commandName)
                    self.commandDescriptions.remove(commandDescription)

    def clear_menu(self):
        # perform checks on a valid input

        for i in range(len(self.commandNames)):
            for j in range(len(self.commandDescriptions)):
                self.commandNames.pop(i)
                self.commandDescriptions.pop(j)
    

async def set_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    bot = Bot("6073682346:AAG3nZhKlApMcO6NownG7ExWJQrZqV6uXIg")
    await bot.set_my_commands([BotCommand(command='start', description='a start test script')])

def main():
    dispatcher.add_handler(CommandHandler("menu", set_menu))
    dispatcher.run_polling()

if __name__ == '__main__':
    main()