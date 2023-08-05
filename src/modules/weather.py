import pyowm
import json
import math
import re

from src import LOGGER, OWM_API_TOKEN, dispatcher
import src.utils.weather_managers as manager

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler, 
    CallbackContext, 
    MessageHandler, 
    ConversationHandler, 
    CallbackQueryHandler,
    filters, 
)

LOGGER.info("Weather: Started initialisation.")

LOCATION_PARAMETER = range(1)


async def request_for_location(update: Update, context: CallbackContext) -> None:
    """entry point to allow the user to specify the location that they wish to send"""

    # first the command will be stored in user_data
    command = (update.message.text.split(' '))[0]
    context.user_data["command"] = command
    LOGGER.info("Weather: Command retrieved from update object.")

    # now we must specify the message_id
    message_id = update.message.message_id
    context.user_data["message_id"] = message_id

    try:
        await update.message.reply_text(
            reply_to_message_id=message_id,
            text="Please enter your location:",
        )
        LOGGER.info("Weather: Location request sent to chat.")
    except:
        LOGGER.error("Weather: Location request was unable to be sent to chat.")

    return LOCATION_PARAMETER # receive weather forecast location data


async def receive_location_parameter(update: Update, context: CallbackContext) -> None:
    """receive the location parameter, ensuring that it's formatted correctly (capitalised)"""
    location_arguments = update.message.text
    location = ""
    location_arguments = list(location_arguments) # to make it mutable

    for index, item in enumerate(location_arguments):
        if (index == 0) or (location_arguments[index-1] == ' '):
            location_arguments[index] = item.upper()
        else:
            location_arguments[index] = item.lower()

        location += location_arguments[index]         
    LOGGER.info("Weather: Location retrieved from update object.")

    # store location in user data dict
    context.user_data["location"] = location

    # retrieve city registry given location
    try:
        await retrieve_city_registries(update, context, OWM_API_TOKEN)
        LOGGER.info("Weather: Called functions for city registries.")
    except:
        LOGGER.error("Weather: Unable to call functions for city registries.")

    return ConversationHandler.END
    

async def retrieve_city_registries(update: Update, context: CallbackContext, api_key: str) -> None:
    """retrieve all the registries with cities that have the same name across the world"""

    try:
        # retrieve location from user data
        location = context.user_data["location"]
        LOGGER.info("Weather: Location retrieved from user data.")
    except KeyError:
        # the location does not exist
        LOGGER.error("Weather: The stored location does not exist.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "Unable to retrieve the location"
        )
        return   
    
    # initialise pyowm manager
    global owm_manager, OWM
    LOGGER.info("Weather: Initialising manager.")
    owm_manager = manager.OWM_API_Manager(api_key)
    OWM = owm_manager.initialise_manager()

    # initialise registry manager
    global registry_manager
    registry_manager = manager.RegistryManager(OWM, location)
    
    # retrieve and store the city registries
    city_registries = registry_manager.get_city_ids()
    context.chat_data[location] = city_registries
    LOGGER.info("Weather: Retrieving city registries from chat data.")
    
    # parse the city registry information together and store in payload or present to end-user
    try:
        await parse_city_registry_information(update, context)
        LOGGER.info("Weather: Attempting to parse city registry information.")
    except:
        LOGGER.error("Weather: Unable to parse city registry information.")
    

async def parse_city_registry_information(update: Update, context: CallbackContext) -> None:
    """parse all the registry information of cities with the same name across the world"""

    # check to ensure that the location key exists
    try:
        # retrieve location and city registries from user data
        location = context.user_data["location"]
        city_registries = context.chat_data[location]
        LOGGER.info("Weather: Retrieving city registries and location from context data for parsing.")
    except KeyError:
        # location does not exist
        LOGGER.error("Weather: The stored location does not exist.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "Unable to retrieve the location",
        )
        return
    
    """if the location only exists in one place then the location"""
    if registry_manager.is_one_location_result(city_registries): # check to see how many returned results are provided.
        LOGGER.info("Weather: Only one location found in registry.")
        city_id = city_registries[0][0]
        name = city_registries[0][1]
        country = city_registries[0][2]   
        if registry_manager.is_state_available(city_registries, 0): 
            state = city_registries[0][3] 
        else:
            state = ''
        lat = city_registries[0][4]
        lon = city_registries[0][5]    
        
        # create payload for location information
        global payload_user_id
        payload_user_id = update.effective_user.id

        payload = {
            payload_user_id: {
                "city_id": city_id,
                "name": name,
                "country": country,
                "state": state,
                "lat": lat,
                "lon": lon,
            }
        }
        context.user_data.update(payload)
        await receive_forecast_command(update, context)

    else: # more than 1 result
        LOGGER.info("Weather: More than one location found in registry.")
        all_city_registries = []

        for i, _ in enumerate(city_registries):
            current_id = city_registries[i][0]
            name = city_registries[i][1]
            country = city_registries[i][2]

            if registry_manager.is_state_available(city_registries, i): 
                state = city_registries[i][3] 
            else:
                state = ''

            lat = city_registries[i][4]
            lon = city_registries[i][5]

            all_city_registries.append([current_id, name, country, state, lat, lon]) # append location information

        bot_message = ""
        bot_message += "It appears that there's more than one location with this name."
        bot_message += "\nPlease select one of the options below\n\n"

        keyboard = []
        count = 0

        while count < len(all_city_registries):
            if all_city_registries[count][3] == '':
                keyboard.append([InlineKeyboardButton(f"{city_registries[count][1]}|{city_registries[count][2]}", callback_data=f"city_id({city_registries[count][0]})")])
            else:
                keyboard.append([InlineKeyboardButton(f"{city_registries[count][1]}|{city_registries[count][2]}|{city_registries[count][3]}", callback_data=f"city_id({city_registries[count][0]})")])

            count += 1   

        reply_markup = InlineKeyboardMarkup(keyboard)

        # send the inline keyboard message
        try:
            await update.message.reply_text(
                reply_to_message_id = context.user_data.get("message_id", "not found"),
                text = bot_message, 
                reply_markup=reply_markup,
            )
            LOGGER.info("Weather: Location selection message was sent to chat.")
        except:
            LOGGER.error("Weather: Location selection message was unable to be sent to chat.")


async def collect_callback_registry_data(update: Update, context: CallbackContext) -> None:
    """the callback function that is called if more than one option is presented in order to retrieve the chosen data."""

    # retrieve the current city location
    try:
        location = context.user_data["location"]
        LOGGER.info("Weather: Location retrieved from user data for callback.")
    except TypeError:
        LOGGER.error("Weather: Location was unable to be retrieved from user data for callback.")
        await update.message.reply_text(
            reply_to_message_id=context.user_data.get("message_id", "not found"),
            text="Unable to retrieve the location.",
        )

    query = update.callback_query
    # Callback Queries need to be answered, even if no notification to the user is needed
    #await query.answer()

    match = re.match(r"city_id\((.+?)\)", query.data)

    try:
        if match:
            city_id = int(match.group(1))
        city_registries = context.chat_data[location]
        LOGGER.info("Weather: City id and registries were retrieved.")
    except TypeError: # unable to retrieve the city registries
        LOGGER.error("Weather: City id and registries were unable to be retrieved.")
        await update.callback_query.message.reply_text(
            reply_to_message_id=context.user_data.get("message_id", "not found"),
            text="Unable to retrieve the city registries.",
        )
        return
    
    #retrieve the respective city registry given the id
    for i, _ in enumerate(city_registries):
        if int(city_registries[i][0]) == int(city_id): # city registry was found
            name = city_registries[i][1]
            country = city_registries[i][2]
            state = city_registries[i][3]
            lat = city_registries[i][4]
            lon = city_registries[i][5]

    # create payload for location information
    
    try:
        global payload_user_id
        payload_user_id = update.callback_query.from_user.id
        payload = {
            payload_user_id: {
                "city_id": city_id,
                "name": name,
                "country": country,
                "state": state,
                "lat": lat,
                "lon": lon,
            }
        }
        LOGGER.info("Weather: City information payload stored in user data.")
        context.user_data.update(payload)
    except NameError:
        LOGGER.error("Weather: City information payload was unable to be stored in user data.")
        await update.callback_query.message.reply_text(
            text="Unable to find the specified city registry.",
        )
        return
    
    try:
        await receive_forecast_command(update, context)
        LOGGER.info("Weather: Attempting to receive the forecast command.")
    except:
        LOGGER.error("Weather: Unable to receive the forecast command.")


async def receive_forecast_command(update: Update, context: CallbackContext) -> None:
    """This function is called after the user has chosen the location and is now ready to receive the forecast command."""

    try:
        command = context.user_data.get("command")
        LOGGER.info("Weather: Command retrieved from user data.")
    except KeyError:
        LOGGER.error("Weather: Unable to retrieve command from user data.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "Unable to retrieve stored command phrase."
        )
        return
    
    # handle the specific call of procedures depending on the command
    if command == "/currentForecast":
        try:
            await receive_current_forecast_data(update, context)
            LOGGER.info("Weather: Attempting to receive the current forecast data.")
        except:
            LOGGER.error("Weather: Unable to call the function for the current forecast data.")
    else:
        """In this case, we must check the duration from the command and what type of command it is."""

        command, duration = command[0:-1], command[-1]

        # now we must store the command and its duration command into user data
        forecast_command_information = [command, duration]
        context.user_data["forecast_command_info"] = forecast_command_information

        if command == "/dayForecast" or command == "/hourForecast":
            try:
                await receive_daily_forecast_data(update, context)
                LOGGER.info("Weather: Attempting to receive the daily forecast data.")
            except:
                LOGGER.error("Weather: Unable to call the function for daily forecast data.")

async def receive_current_forecast_data(update: Update, context: CallbackContext) -> None:
    """retrieve the data for the current weather forecast"""

    try:
        location_dict = context.user_data.get(payload_user_id)
        LOGGER.info("Weather: The location payload has been retrieved from user data.")
    except KeyError:
        LOGGER.error("Weather: The location payload was unable to be retrieved from user data.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text="Unable to retrieve location information."
        )
    
    # retrieve the location information
    name = location_dict['name']
    country, state = location_dict['country'], location_dict['state']
    lat, lon = location_dict['lat'], location_dict['lon']
    weather_manager = manager.WeatherManager(lat, lon)
    
    response = weather_manager.request_weather()

    try:
        if response is not None: # valid response
            # parse the json data
            forecast_json_data = json.loads(response.text)
            main_data = forecast_json_data["main"]
            description = forecast_json_data["weather"][0]["description"] 
            description += f" {weather_manager.return_description_emoji(description)}"
            wind_data = forecast_json_data["wind"]
            temp, temp_min, temp_max = main_data["temp"], main_data["temp_min"], main_data["temp_max"]
            humidity, windspeed = main_data["humidity"], wind_data["speed"]

            payload = {
                "current_weather": {
                    "location_name": name,
                    "country": country,
                    "state": state,
                    "description": description,
                    "current_temp": temp,
                    "min_temp": temp_min,
                    "max_temp": temp_max,
                    "humidity": humidity,
                    "windspeed": windspeed
                }
            }
            LOGGER.info("Weather: Storing weather information payload in user data.")
            context.user_data.update(payload)
        else:
            LOGGER.error("Weather: Unable to retrieve a valid response to parse weather information.")
            await update.message.reply_text(
                reply_to_message_id = context.user_data.get("message_id", "not found"),
                text = "Unable to retrieve the weather data html page."
            )
            return     
    except NameError:
        LOGGER.error("Weather: Unable to retrieve the weather response due to a key error.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "There was an issue with retrieving the weather data from the weather API."
        )
        return
    
    try:
        await output_current_weather_data(update, context)
        LOGGER.info("Weather: Called function to output the weather data.")
    except:
        LOGGER.error("Weather: Unable to call function in order to output the weather data.")


async def output_current_weather_data(update: Update, context: CallbackContext) -> None:
    """the function that will retrieve the final current weather information and output it to the user"""

    # attempt to receive the current weather data
    try:
        weather_data = context.user_data.get("current_weather", "not found")
        LOGGER.info("Weather: Weather payload information has been retrieved from user data.")
    except KeyError:
        LOGGER.error("Weather: Unable to retrieve weather payload information from user data.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "Unable to retrieve the current weather data from context."
        )
        return
    
    message = ""

    if weather_data["state"] != None:
        message += f"WEATHER INFORMATION: {weather_data['location_name']}, {weather_data['country']}, {weather_data['state']}\n\t"
    else:
        message += f"WEATHER INFORMATION: {weather_data['location_name']}, {weather_data['country']}\n\t"

    message += f"""
    current_status -> {weather_data["description"]}
    current_temp -> {math.ceil(weather_data["current_temp"])}°C
    min temp -> {math.ceil(weather_data["min_temp"])}°C
    max temp -> {math.ceil(weather_data["max_temp"])}°C
    humidity -> {weather_data["humidity"]}%rh
    wind speed -> {math.ceil(weather_data["windspeed"])}mph
    """

    if update.message is None:
        await update.callback_query.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = message
        )
        LOGGER.info("Weather: Current weather data is being sent to chat via callback.")
    else:
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = message
        )
        LOGGER.info("Weather: Current weather data is being sent to chat.")


async def receive_daily_forecast_data(update: Update, context: CallbackContext) -> None:
    """retrieve the weather forecast for a location that specifies the conditions over the next few days"""

    # we'll start by attempting to receive the location information that was parsed into a payload earlier
    try:
        location_information = context.user_data.get(payload_user_id)
        LOGGER.info("Weather: The location payload has been retrieved from user data.")
    except KeyError:
        LOGGER.error("Weather: The location payload was unable to be retrieved from user data.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text="Unable to retrieve location information."
        )

    # next we'll try to attempt to receive the duration for the forecast command that was stored in user context
    try:
        command = context.user_data.get("forecast_command_info")[0]
        duration = int(context.user_data.get("forecast_command_info")[1])
        LOGGER.info("Weather: The command and duration have been retrieved from user data.")
    except KeyError:
        LOGGER.error("Weather: The command and duration were unable to be retrieved from user data.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "Unable to retrieve the stored duration of the forecast command."
        )

    # retrieve the location information
    location_info = registry_manager.get_location_information(location_information)
    name, country, state, lat, lon = location_info[0], location_info[1], location_info[2], location_info[3], location_info[4]
    
    if command == "/dayForecast":
        cnt = 8 * duration
    elif command == "/hourForecast":
        cnt = duration
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&units=metric&cnt={cnt}&appid={OWM_API_TOKEN}"
    response = owm_manager.request_api(url)
    
    try:
        if response is not None:
            # parse the json data
            forecast_json_data = json.loads(response.text)
            forecast_list = forecast_json_data["list"]
            forecast_payload = {}

            if command == "/dayForecast":
                condition = int(cnt/8)
            elif command == "/hourForecast":
                condition = int(cnt)

            for index in range(condition):
                if command == "/dayForecast":
                    dt_text = forecast_list[(8*index)]["dt_txt"].split(' ')[0]
                    number_of_hourly_periods = 8 * index
                    hour_period_condition = (8 * (index + 1))
                elif command == "/hourForecast":
                    dt_text = f"{forecast_list[(index)]['dt_txt'].split(' ')[0]} {forecast_list[(index)]['dt_txt'].split(' ')[1]}"
                    number_of_hourly_periods = index
                    hour_period_condition = cnt

                total_temp = total_humidity = total_wind_speed = 0
                                
                while number_of_hourly_periods < hour_period_condition:
                    # data type ideas for this data
                    # {"dt_text" [avg_temp, avg_humidity, avg_wind_speed, min_temp, max_temp]

                    # increment the number of periods in that day to help and work out the average temperature

                    temp = forecast_list[number_of_hourly_periods]["main"]["temp"]
                    humidity = forecast_list[number_of_hourly_periods]["main"]["humidity"]
                    wind_speed = forecast_list[number_of_hourly_periods]["wind"]["speed"]

                    current_min_temp = forecast_list[number_of_hourly_periods]["main"]["temp_min"]
                    current_max_temp = forecast_list[number_of_hourly_periods]["main"]["temp_max"]

                    # add to the total values to help before calculatng an average
                    total_temp, total_humidity, total_wind_speed = (total_temp + temp), total_humidity + humidity, (total_wind_speed + wind_speed)
                    
                    if command == "/dayForecast":
                        should_set_temp_range = (number_of_hourly_periods == 0) or (number_of_hourly_periods % 8 == 0)
                    elif command == "/hourForecast":
                        should_set_temp_range = number_of_hourly_periods == 0

                    if should_set_temp_range: # it is on the first iteration of each change in index
                        # first set the min/max temps that can be compared to later values to determine whether they are smaller or greater than the previous
                        min_temp = current_min_temp
                        max_temp = current_max_temp
                    else:
                        # in other cases we will compare the different values to see whether they are higher or lower than before
                        if min_temp > current_min_temp:
                            min_temp = current_min_temp
                        
                        if max_temp < current_max_temp:
                            max_temp = current_max_temp
                    
                    number_of_hourly_periods += 1 

                # average out each of the values
                avg_temp = math.ceil(total_temp / 8)
                avg_humidity = math.ceil(total_humidity / 8)
                avg_wind_speed = math.ceil(total_wind_speed / 8)

                forecast_payload[dt_text] = {
                    "avg_temp": avg_temp, 
                    "avg_humidity": avg_humidity, 
                    "avg_wind_speed": avg_wind_speed, 
                    "min_temp": math.ceil(min_temp),
                    "max_temp": math.ceil(max_temp)
                    }

            payload = {
            "name": name,
            "country": country,
            "state": state,
            "weather_forecast": forecast_payload
            }                        
            # store the forecast
            LOGGER.info("Weather: Storing forecast information payload in user data.")
            context.user_data.update(payload)
        else:
            LOGGER.error("Weather: Unable to retrieve a valid response to parse forecast information.")
            await update.message.reply_text(
                reply_to_message_id = context.user_data.get("message_id", "not found"),
                text = "Unable to retrieve the forecast data html page."
            )
            return  
    except NameError:
        LOGGER.error("Weather: Unable to retrieve the forecast response due to a key error.")
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = "There was an issue with retrieving the forecast data from the weather API."
        )
        return
    
    try:
        await output_weather_forecast(update, context)
        LOGGER.info("Weather: Called function to output the forecast data.")
    except:
        LOGGER.error("Weather: Unable to call function to output the forecast data.")

async def output_weather_forecast(update: Update, context: CallbackContext) -> None:
    """this is the function that will output the weather forecast for the chosen location"""

    # first attempt to retrieve the stored forecast data
    try:
        forecast_payload = context.user_data.get("weather_forecast", "not found")
        name = context.user_data.get("name", "not found")
        country = context.user_data.get("country", "not found")
        state = context.user_data["state"]
        LOGGER.info("Weather: Stored forecast information has been retrieved from user data.")
    except KeyError:
        LOGGER.error("Weather: Unable to retrieve the forecast information from user data.")
        await update.message.reply_text(
            "Unable to retrieve the current forecast data from context."
        )
        return
    
    if state == None:
        message = f"WEATHER FORECAST INFORMATION:\n{name}|{country}\n"
    else:
        message = f"WEATHER FORECAST INFORMATION:\n{name}|{country}|{state}\n"
    
    LOGGER.info("Weather: Parsing forecast information.")
    for key, item in forecast_payload.items():
        message += f"\n{key}:\n"
        message += f"Avg temp: {item['avg_temp']}\n"
        message += f"Min temp / Max temp: {item['min_temp']}/{item['max_temp']}\n"
        message += f"Avg humidity: {item['avg_humidity']}%rh, Avg wind speed: {item['avg_wind_speed']}mph\n"   

    if update.message is None:
        await update.callback_query.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = message
        )
        LOGGER.info("Weather: Forecast data is being sent to chat via callback.")
    else:
        await update.message.reply_text(
            reply_to_message_id = context.user_data.get("message_id", "not found"),
            text = message
        )
        LOGGER.info("Weather: Forecast data is being sent to chat.")

async def retrieve_geocodes(update: Update, context: CallbackContext, location_name, api_key: str) -> None:
    # initialise pyowm manager
    owm = pyowm.OWM(OWM_API_TOKEN)
    manager = owm.weather_manager()

    # obtain ids
    reg = owm.city_id_registry()

    # get the city ID given its name
    global city_registries
    city_registries = reg.ids_for(location_name, matching='exact') # will exact check
 

async def cancel_weather(update: Update, context: CallbackContext) -> None:
    """cancels and ends the conversation."""
    LOGGER.info("Weather: Retrieving the username of the user that sent the cancel message.")
    user = update.message.from_user # user id
    LOGGER.info("Weather: User %s cancelled the conversation.")
    
    # send message below with information

    try:
        await update.message.reply_text(
            f"That's alright {user}! Just call the necessary command if you'd like to retrieve weather information again."
        )
        LOGGER.info("Weather: Weather cancel information has been sent to chat.")
    except:
        LOGGER.error("Weather: Weather cancel information was unable to be sent to chat.")

    return ConversationHandler.END # return the end of the conversation


__module_name__ = "Weather"
__help__ = """
• `/currentForecast` - Get the current weather forecast for a location

• `/dayForecast[n]` - Get the weather forecast for the next n days (range of n is 1 to 5), e.g /dayForecast3

• `/hourForecast[n]` - Get the weather forecast for the next n 3 HOUR PERIODS (range of n is 1 to 8), e.g /hourForecast4 -> next (4 x 3) = 12 hours from now.
"""

weather_forecast_handler = ConversationHandler(
    entry_points=[
        CommandHandler("currentForecast", request_for_location),                # Handle entry point for the current forecast
        CommandHandler("dayForecast2", request_for_location),                   # Handle entry point for a 2 day forecast
        CommandHandler("dayForecast3", request_for_location),                   # Handle entry point for a 3 day forecast
        CommandHandler("dayForecast4", request_for_location),                   # Handle entry point for a 4 day forecast
        CommandHandler("dayForecast5", request_for_location),                   # Handle entry point for a 5 day forecast
        CommandHandler("hourForecast1", request_for_location),                  # Handle entry point for a 1 3 hour step forecast
        CommandHandler("hourForecast2", request_for_location),                  # Handle entry point for a 2 3 hour step forecast
        CommandHandler("hourForecast3", request_for_location),                  # Handle entry point for a 3 3 hour step forecast
        CommandHandler("hourForecast4", request_for_location),                  # Handle entry point for a 4 3 hour step forecast
        CommandHandler("hourForecast5", request_for_location),                  # Handle entry point for a 5 3 hour step forecast
        CommandHandler("hourForecast6", request_for_location),                  # Handle entry point for a 6 3 hour step forecast
        CommandHandler("hourForecast7", request_for_location),                  # Handle entry point for a 7 3 hour step forecast
        CommandHandler("hourForecast8", request_for_location)                   # Handle entry point for a 8 3 hour step forecast
    ],
    states={
        LOCATION_PARAMETER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_location_parameter)]
    },
    fallbacks=[CommandHandler("cancel", cancel_weather)]
)

REGISTRY_DATA_HANDLER = CallbackQueryHandler(collect_callback_registry_data, pattern=r"city_id")

dispatcher.add_handler(weather_forecast_handler)
dispatcher.add_handler(REGISTRY_DATA_HANDLER)