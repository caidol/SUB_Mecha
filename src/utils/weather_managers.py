import requests
import pyowm
import json
import pyowm
from typing import Tuple, Optional

from src import LOGGER, OWM_API_TOKEN


class OWM_API_Manager:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/"
        self.units = "metric" # allow the user to change this in settings later on

    def initialise_manager(self) -> str:
        # initialise the manager with the api key 
        # -> NOTE: this is used instead of directly requesting the API as it returns more results per location

        return pyowm.OWM(self.api_key)
    

    def request_api(self, request_url) -> str:
        """
        Requests the OpenWeatherMap API.
        :param query_string: The query string to request the API with.
        :return: The API data.
        """
        # perform request on API url
        response = requests.get(request_url)

        if response.status_code != 200:
            LOGGER.error("The request was unsuccessful. Status code: " + str(response.status_code))
            return None
        
        return response

# child classes

class LocationManager(OWM_API_Manager):
    def __init__(self, location, city_name, country_code, state_code) -> None:
        OWM_API_Manager.__init__(self, OWM_API_TOKEN)
        self.location = location
        self.geocode_url = "http://api.openweathermap.org/geo/1.0/direct?"
        self.forecast_query_string = "forecast?"
        self.city_name = city_name
        self.country_code = country_code
        self.state_code = state_code


    def request_geocodes(self, city_name, country_code, state_code) -> str:
        """
        Requests the geocode data from the OpenWeatherMap API.
        :param city_name: The city name to request the geocode data for.
        :param country_code: The country code to request the geocode data for.
        :param state_code: The state code to request the geocode data for.
        :return: The geocode data.
        """
        # -> NOTE: this is used instead of directly requesting the API as it returns more accurate results per location
        
        url = f"{self.geocode_url}q={city_name},{state_code},{country_code}&appid={self.api_key}"

        geocode_data = self.request_api(url) # request the API -> method from parent class

        if geocode_data is None:
            return geocode_data
        
        return json.loads(geocode_data)
    

    def get_geocodes(self, city_name, country_code, state_code: str, update) -> None: # I prefer getting the geocodes from the API instead of from the pyOWM module as it's more accurate
        # retrieve url data using the request geocode method   
        geocode_data = self.request_geocodes(city_name, country_code, state_code)

        if geocode_data != None: # successful API response
            #print(geocode_data)

            geocode_data = geocode_data[0] # get the first result from the list -> as we have provided the exact location name, there should only be one result
            
            return [geocode_data['lat'], geocode_data['lon']] # return the latitude and longitude of the location
        
        else: # Should run but it doesn't. Fix later
            print("does not exist")
        

    def get_population(self) -> int:
        complete_url = f"{self.base_url}{self.forecast_query_string}q={self.city_name},{self.state_code},{self.country_code}&appid={self.api_key}"

        location_data = self.request_api(complete_url) # request the API -> method from parent class

        if location_data is None:
            return location_data
        
        print(location_data)

        return location_data["population"]


class WeatherManager(OWM_API_Manager):
    def __init__(self, lat, lon) -> None:
        OWM_API_Manager.__init__(self, OWM_API_TOKEN)
        self.weather_query_string = "weather?"
        self.lat = lat 
        self.lon = lon
        self.descriptions = {
            "clear sky": "☀️",
            "few clouds": "🌤️",
            "scattered clouds": "🌥️",
            "broken clouds": "☁️",
            "shower rain": "🌧️",
            "rain": "🌧️",
            "thunderstorm": "🌩️",
            "snow": "🌨️",
            "mist": "🌫️"
        }


    def request_weather(self) -> str:
        """
        Requests the weather data from the OpenWeatherMap API.

        :param city_name: The name of the city to get the weather data for.
        :return: The weather data.
        """

        complete_url = f"{self.base_url}{self.weather_query_string}lat={self.lat}&lon={self.lon}&appid={self.api_key}&units={self.units}"
        print("COMPLETE URL: " + complete_url)

        # check to see whether the request was successful
        weather_data = self.request_api(complete_url) # request the API -> method from parent class

        return weather_data
    
    def return_description_emoji(self, description) -> str:
        # returns the emoji corresponding to the description
        for key, value in self.descriptions.items():
            if key == description:
                return value
            
        return ""


class RegistryManager(OWM_API_Manager):
    """
    This class is used to store a list of cities and their corresponding weather data.
    """

    def __init__(self, owm, location_name) -> None:
        OWM_API_Manager.__init__(self, OWM_API_TOKEN)
        self.owm = owm
        self.location_name = location_name


    def get_city_ids(self) -> list:
        # obtain complete registry with city id's
        registry = self.owm.city_id_registry()

        return registry.ids_for(self.location_name, matching='exact') # exact match for now


    def get_location_information(self, location_dict) -> Tuple[str, str, Optional[str], str, str]:
        # returns the location information from the dictionary

        return location_dict['name'], location_dict['country'], location_dict['state'], location_dict['lat'], location_dict['lon']
    

    def is_one_location_result(self, registry) -> bool:
        # Returns true if the length of the registry is 1, otherwise false
        
        if len(registry) == 1:
            return True
        
        return False
    

    def is_state_available(self, registry, iteration) -> bool:
        # Returns true if the placeholder for the state index is not referenced as 'None'
        
        if registry[iteration][3] != None:
            return True
        
        return False