
This quickstart guides you through setting up a workflow that involves multiple steps: first, retrieving the latitude and longitude for a given city name, and second, using those coordinates to fetch the current temperature. This workflow consults two different APIs and logs the results. We will run this locally using the terminal.

## Project Structure

You will need to create the following structure:

```text
.
├── hook
│   └── api.py
├── operator
│   └── weather.py
├── pyproject.toml
├── Makefile
└── .env
```

Create the hook and operator folders like this:

```bash
mkdir hook operator
```

## hook.py

We will create a hook that interacts with two external APIs:
1.  [geocode.xyz](https://geocode.xyz/): To get latitude and longitude from a city name.
2.  [open-meteo](https://open-meteo.com/): To get the current weather using latitude and longitude.

```python title="hook/api.py"
import requests
from urllib.parse import quote
from typing import Tuple, Dict, Any

from airless.core.hook import BaseHook


class ApiHook(BaseHook): # (1)!
    """A hook to fetch geocode data and weather information."""

    def __init__(self):
        """Initializes the ApiHook."""
        super().__init__()
        self.weather_base_url = 'https://api.open-meteo.com/v1/forecast'
        self.geocode_base_url = 'https://geocode.xyz'

    def _get_geocode_headers(self) -> Dict[str, str]: # (2)!
        """Returns headers needed for the geocode.xyz API request."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9', # Changed to en-US for broader compatibility
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }

    def get_lat_long_from_city(self, city_name: str) -> Tuple[float, float]: # (3)!
        """
        Fetch the latitude and longitude for a given city name using geocode.xyz.

        Args:
            city_name (str): The name of the city.

        Returns:
            Tuple[float, float]: A tuple containing latitude and longitude.

        Raises:
            requests.exceptions.RequestException: If the API request fails.
            KeyError: If the expected keys ('latt', 'longt') are not in the response.
        """
        url = f"{self.geocode_base_url}/{quote(city_name)}?json=1"
        headers = self._get_geocode_headers()

        with requests.Session() as session:
            response = session.get(url, headers=headers)
            response.raise_for_status() # (4)!
            data = response.json()
            self.logger.debug(f"Geocode response data: {data}")

            latitude = float(data['latt'])
            longitude = float(data['longt'])

            return latitude, longitude

    def get_temperature(self, lat: float, lon: float) -> float: # (5)!
        """
        Fetch the current temperature for given latitude and longitude using Open-Meteo.

        Args:
            lat (float): The latitude.
            lon (float): The longitude.

        Returns:
            float: The current temperature in Celsius.

        Raises:
            requests.exceptions.RequestException: If the API request fails.
            KeyError: If the expected keys are not in the response.
        """
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m'
        }
        with requests.Session() as session: # (6)!
            response = session.get(
                self.weather_base_url,
                params=params
            )
            response.raise_for_status() # (4)!
            data = response.json()
            self.logger.debug(f"Weather response data: {data}")

            temperature = data['current']['temperature_2m']

            return temperature

```

1.  To create a hook, inherit from `#!python BaseHook`.
2.  We separate the header generation for the `geocode.xyz` API into its own method `_get_geocode_headers` for clarity and potential reuse.
3.  The `get_lat_long_from_city` method takes a city name, constructs the URL for `geocode.xyz`, calls the API using the headers from `_get_geocode_headers`, parses the JSON response, and returns the latitude and longitude. It includes basic error handling for empty city names and missing keys in the response.
4.  Use `#!python response.raise_for_status()` to raise an HTTPError for bad responses (4xx or 5xx). This helps in catching API errors early.
5.  The `get_temperature` method remains similar, taking latitude and longitude to query the Open-Meteo API for the current temperature. Error handling for the response structure is added.
6.  Use `#!python requests.Session()` to manage connections efficiently and ensure resources are properly closed.

## operator.py

Now, we create an operator that uses the `ApiHook`. This operator will handle two types of requests: one to get the latitude and longitude for a city, and another to get the temperature using provided latitude and longitude.

```python title="operator/weather.py"
from airless.core.operator import BaseOperator

from hook.api import ApiHook


class WeatherOperator(BaseOperator): # (1)!
    """
    An operator to fetch geographic coordinates for a city
    or weather data using coordinates.
    """

    def __init__(self):
        """Initializes the WeatherOperator."""
        super().__init__()
        self.api_hook = ApiHook()

    def execute(self, data: dict, topic: str) -> None: # (2)!
        """
        Routes the request to the appropriate method based on 'request_type'.
        """
        request_type = data['request_type']

        if request_type == 'temperature':
            self.get_temperature(data, topic)
        elif request_type == 'city_lat_long':
            self.get_city_lat_long(data, topic)
        else:
            self.logger.error(f"Request type '{request_type}' not implemented or missing.")

    def get_city_lat_long(self, data: dict, topic: str) -> None: # (4)!
        """Fetch the latitude and longitude for a given city name."""
        city_name = data['city_name']

        latitude, longitude = self.api_hook.get_lat_long_from_city(city_name)
        self.logger.info(f"Successfully fetched coordinates for city: {city_name}.") # (3)!
        self.logger.info(f"Coordinates for {city_name}: Latitude={latitude}, Longitude={longitude}")

    def get_temperature(self, data: dict, topic: str) -> None:
        """Fetch the current temperature for given coordinates."""
        lat = data['lat']
        lon = data['lon']

        temperature = self.api_hook.get_temperature(lat, lon)
        self.logger.info(f"Successfully fetched temperature for ({lat}, {lon}).") # (3)!
        self.logger.info(f"Temperature at ({lat}, {lon}): {temperature}°C")

```

1.  To create an operator, inherit from `#!python BaseOperator`.
2.  The `execute` method acts as a router. It checks the `request_type` field in the input `data` dictionary and calls the corresponding method (`get_temperature` or `get_city_lat_long`).
3.  `#!python BaseOperator` provides a built-in `#!python self.logger` for logging messages.
4.  The new `get_city_lat_long` method extracts the `city_name` from the data, calls the corresponding hook method (`get_lat_long_from_city`), and logs the result or any errors encountered. Basic validation for the presence of `city_name` is added.

## Makefile and .env
In the root directory create a `Makefile` and a `.env` file.

First, create the files:
```bash
touch Makefile .env
```

In the `Makefile`, add commands to run both types of requests:

??? Warning
    Makefile indentation must use tabs, not spaces.

```makefile
run-temp:
	@python -c "from operator.weather import WeatherOperator; WeatherOperator().execute(data={'request_type': 'temperature', 'lat': 40.7128, 'lon': -74.0060}, topic='test-topic')"

run-latlong:
	@python -c "from operator.weather import WeatherOperator; WeatherOperator().execute(data={'request_type': 'city_lat_long', 'city_name': 'New York'}, topic='test-topic')"
```

In the `.env` file, add the following environment variables:

```env title=".env"
ENV=dev
LOG_LEVEL=DEBUG
```
Setting `LOG_LEVEL=DEBUG` will ensure you see the detailed logs from the hook and operator, including API responses. Change to `INFO` for less verbose output.

## Run

To run the operator for a specific task, use the corresponding `make` target. `uv run` handles loading the `.env` file automatically. If not using `uv`, ensure environment variables are exported or use a library like `python-dotenv`.

To get coordinates for a city (e.g., New York):
```bash
uv run --env-file .env make run-latlong
```

To get the temperature for specific coordinates (e.g., New York's approx. coordinates):
```bash
uv run --env-file .env make run-temp
```

You should see log output in your terminal showing the API calls and the results (coordinates or temperature), or error messages if something went wrong.