
This quickstart guides you through deploying a workflow to Google Cloud Platform (GCP) that involves multiple steps: first, retrieving the latitude and longitude for a given city name, and second, using those coordinates to fetch the current temperature. This workflow consults two different APIs and logs the results. We will deploy this using Terraform and trigger it via Pub/Sub messages.

This quickstart assumes you have:

* A local IDE (VS Code, PyCharm, etc.) with Python 3.9+.
* Terminal access.
* A Google Cloud Platform account with billing enabled.
* The `gcloud` CLI installed and configured ([link](https://cloud.google.com/sdk/docs/install)).
* Terraform installed ([link](https://developer.hashicorp.com/terraform/install)).
* Core infrastructure module already defined. ([link](./core-infrastructure.md))

## Project Structure

You will need to create the following structure:

```text
.
├── hook
│   └── api.py           # Hook to interact with external APIs
├── operator
│   └── weather.py       # Operator containing business logic
├── terraform
│   ├── main.tf          # Terraform main configuration (provider, backend, archive)
│   ├── function.tf      # Terraform resources for Pub/Sub and Cloud Function
│   └── variables.tf     # Terraform input variables
├── main.py              # Cloud Function entry point
├── requirements.txt     # Python dependencies
├── Makefile             # Helper commands for deployment and triggering
└── .env                 # Environment variables for local Terraform execution
```

Create the necessary folders:

```bash
mkdir hook operator terraform
touch hook/api.py operator/weather.py terraform/main.tf terraform/function.tf terraform/variables.tf main.py requirements.txt Makefile .env
```

## hook.py

We will reuse the hook from the local example, as its core function—interacting with external APIs—remains the same. It interacts with [geocode.xyz](https://geocode.xyz/) and [open-meteo.com](https://open-meteo.com/).

```python title="hook/api.py"
import requests
from urllib.parse import quote
from typing import Tuple, Dict, Any

from airless.core.hook import BaseHook # (1)!


class ApiHook(BaseHook):
    """A hook to fetch geocode data and weather information."""

    def __init__(self):
        """Initializes the ApiHook."""
        super().__init__()
        self.weather_base_url = 'https://api.open-meteo.com/v1/forecast'
        self.geocode_base_url = 'https://geocode.xyz'

    def _get_geocode_headers(self) -> Dict[str, str]:
        """Returns headers needed for the geocode.xyz API request."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
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

    def get_lat_long_from_city(self, city_name: str) -> Tuple[float, float]: # (2)!
        """
        Fetch the latitude and longitude for a given city name using geocode.xyz.
        """
        url = f"{self.geocode_base_url}/{quote(city_name)}?json=1"
        headers = self._get_geocode_headers()

        with requests.Session() as session:
            response = session.get(url, headers=headers)
            response.raise_for_status() # (3)!
            data = response.json()
            self.logger.debug(f"Geocode response data: {data}")

            latitude = float(data['latt'])
            longitude = float(data['longt'])

            return latitude, longitude

    def get_temperature(self, lat: float, lon: float) -> float: # (4)!
        """
        Fetch the current temperature for given latitude and longitude using Open-Meteo.
        """
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m'
        }
        with requests.Session() as session: # (5)!
            response = session.get(
                self.weather_base_url,
                params=params
            )
            response.raise_for_status() # (3)!
            data = response.json()
            self.logger.debug(f"Weather response data: {data}")

            temperature = data['current']['temperature_2m']

            return temperature

```

1.  Inherits from `#!python BaseHook` (assuming your package provides this generic base).
2.  Method to fetch latitude and longitude for a city.
3.  Raises an `HTTPError` for bad API responses (4xx or 5xx).
4.  Method to fetch temperature using latitude and longitude.
5.  Uses `#!python requests.Session()` for efficient connection management.

## operator.py

The operator now inherits from a GCP-specific base class (`GoogleBaseEventOperator`) which knows how to handle Pub/Sub CloudEvents. The core logic using the `ApiHook` remains.

The base operator (`GoogleBaseEventOperator`) is designed to handle Pub/Sub events and includes error routing. Uncaught exceptions during execution are typically caught by the base operator or the framework and sent to a designated error topic (configured via the `QUEUE_TOPIC_ERROR` environment variable). This ensures that errors don't cause the function to crash silently and can be processed separately.

```python title="operator/weather.py"
from airless.google.cloud.core.operator import GoogleBaseEventOperator # (1)!
from airless.core.utils import get_config # (2)!

from hook.api import ApiHook


class WeatherOperator(GoogleBaseEventOperator): # (3)!
    """
    An operator to fetch geographic coordinates for a city
    or weather data using coordinates, triggered by Pub/Sub events.
    """

    def __init__(self):
        """Initializes the WeatherOperator."""
        super().__init__()
        self.api_hook = ApiHook()

    def execute(self, data: dict, topic: str) -> None: # (4)!
        """
        Routes the request based on 'request_type' from the Pub/Sub message data.
        """
        request_type = data.get('request_type') # Use .get for safer access

        if request_type == 'temperature': # (5)!
            self.get_temperature(data, topic)
        elif request_type == 'city_lat_long':
            self.get_city_lat_long(data, topic)
        else:
            # Error logging is handled by the base operator via report_error
            # if an exception is raised, or log manually if it's a known invalid state.
            self.logger.error(f"Request type '{request_type}' not implemented or missing.")
            # Optionally raise an exception to trigger error routing:
            # raise ValueError(f"Invalid request_type: {request_type}")

    def get_city_lat_long(self, data: dict, topic: str) -> None:
        """Fetch the latitude and longitude for a given city name."""
        city_name = data.get('city_name')
        if not city_name:
            self.logger.error("Missing 'city_name' in request data.")
            raise ValueError("Missing 'city_name'") # Trigger error routing

        try:
            latitude, longitude = self.api_hook.get_lat_long_from_city(city_name)
            self.logger.info(f"Successfully fetched coordinates for city: {city_name}.")
            self.logger.info(f"Coordinates for {city_name}: Latitude={latitude}, Longitude={longitude}")
            # Publish to the same topic with a different request type to get the temperature
            self.queue_publish(topic, {"request_type": "temperature", "lat": latitude, "lon": longitude}) # (6)!
        except Exception as e:
            self.logger.error(f"Error fetching lat/long for {city_name}: {e}")
            # Re-raise to let the base operator handle error routing
            raise

    def get_temperature(self, data: dict, topic: str) -> None:
        """Fetch the current temperature for given coordinates."""
        lat = data.get('lat')
        lon = data.get('lon')
        if lat is None or lon is None:
            self.logger.error("Missing 'lat' or 'lon' in request data.")
            raise ValueError("Missing 'lat' or 'lon'") # Trigger error routing

        try:
            temperature = self.api_hook.get_temperature(lat, lon)
            self.logger.info(f"Successfully fetched temperature for ({lat}, {lon}).")
            self.logger.info(f"Temperature at ({lat}, {lon}): {temperature}°C")
            # If you need to send results elsewhere, do it here.
        except Exception as e:
            self.logger.error(f"Error fetching temperature for ({lat}, {lon}): {e}")
            # Re-raise to let the base operator handle error routing
            raise

```

1.  Import the base operator designed for GCP Pub/Sub events.
2.  Import utility to get environment variables configured in Terraform.
3.  Inherit from `#!python GoogleBaseEventOperator`.
4.  The `execute` method now receives the decoded Pub/Sub message `data` and the `topic` name. The base class handles the CloudEvent decoding.
5.  The `execute` method routes the request based on 'request_type' from the Pub/Sub message data.
6.  The `get_city_lat_long` method fetches the latitude and longitude for a given city name and publishes a new message to the same topic with a different request type to get the temperature.

## main.py

This is the entry point for the Google Cloud Function. It uses the `functions-framework` and dynamically imports the operator specified by the `OPERATOR_IMPORT` environment variable.

```python title="main.py"
import functions_framework
import os

from airless.core.utils import get_config

# Dynamically import the operator based on environment variable
exec(f'{get_config("OPERATOR_IMPORT")} as OperatorClass') # (1)!

@functions_framework.cloud_event # (2)!
def route(cloud_event):
    """
    Cloud Function entry point triggered by a Pub/Sub event.
    Dynamically routes the event to the appropriate Airless operator.
    """
    # Instantiate the dynamically loaded operator class
    operator_instance = OperatorClass()
    # Run the operator with the incoming event data
    operator_instance.run(cloud_event) # (3)!

```

1.  `exec(f'{get_config("OPERATOR_IMPORT")} as OperatorClass')` dynamically imports the operator class based on the `OPERATOR_IMPORT` environment variable (defined in Terraform). This makes the `main.py` reusable.
2.  `@functions_framework.cloud_event` decorator registers this function to handle Cloud Events.
3.  `operator_instance.run(cloud_event)` is called. The `GoogleBaseEventOperator`'s `run` method parses the `cloud_event` (decoding the Pub/Sub message data) and then calls the `execute` method you defined in `WeatherOperator` with the extracted `data` and `topic`.

## requirements.txt

List the necessary Python packages for the Cloud Function.

```text title="requirements.txt"
airless-google-cloud-core~=0.1.2
```

## .env

This file is primarily used to provide variables to Terraform when running *locally*. The deployed function uses environment variables set directly in its Terraform configuration.

```dotenv title=".env"
# Environment Name (used for naming resources)
ENV=dev

# Logging Level for local testing (Cloud Function level set in Terraform)
LOG_LEVEL=DEBUG

# --- GCP Configuration ---
# Replace with your actual GCP Project ID
GCP_PROJECT="your-gcp-project-id"
QUEUE_TOPIC_ERROR="dev-airless-error"
```

!!! warning
    Ensure this file is added to your `.gitignore` to avoid committing sensitive information like secrets if applicable.

## Makefile

Create a `Makefile` to simplify deployment and testing commands.

!!! warning "Makefile Indentation"
    Remember that Makefiles use **tabs** for indentation, not spaces.

```makefile title="Makefile"

run:
  @python -c "from operator.weather import WeatherOperator; WeatherOperator().execute({'request_type': 'temperature', 'lat': 51.5074, 'lon': -0.1278})"

```

This Makefile provides convenient targets:

* `make run`: Runs the operator locally.

## Terraform Configuration

We'll use Terraform to define the GCP infrastructure: a Pub/Sub topic to trigger the function and the Cloud Function itself.

### variables.tf

Defines the input variables for our Terraform configuration.

```terraform title="terraform/variables.tf"
variable "project_id" {
  description = "The GCP project ID."
  type        = string
}

variable "region" {
  description = "The GCP region to deploy resources in."
  type        = string
  default     = "us-central1" # Or your preferred region
}

variable "env" {
  description = "Deployment environment (e.g., dev, prod)."
  type        = string
  default     = "dev"
}

variable "log_level" {
  description = "Logging level for the Cloud Function."
  type        = string
  default     = "INFO"
}

variable "function_bucket_name" {
  description = "Name of the GCS bucket to store Cloud Function source code."
  type        = string
  # Example: default = "your-prefix-cloud-functions-source"
}

variable "pubsub_topic_error_name" {
  description = "Name of the Pub/Sub topic for routing function errors."
  type        = string
  default     = "dev-airless-error" # Example, adjust as needed
}

variable "function_name" {
  description = "Base name for the Cloud Function."
  type        = string
  default     = "weather-api"
}

variable "source_archive_exclude" {
  description = "Files/directories to exclude from the source code archive."
  type        = set(string)
  default = [
    ".venv",
    ".git",
    ".terraform",
    "__pycache__",
    "*.pyc",
    "*.zip" # Exclude the output zip itself
  ]
}
```

### main.tf

Configures the Terraform provider, backend (optional but recommended), and defines the process for archiving the source code.

```terraform title="terraform/main.tf"
# Archive the source code directory into a zip file
data "archive_file" "source" {
  type        = "zip"
  source_dir  = "${path.module}/" # Zips the current directory
  output_path = "/tmp/${var.env}-${var.function_name}-source.zip"
  excludes    = var.source_archive_exclude

  # Include necessary files/dirs explicitly if source_dir is broader
  # For this structure, source_dir = "." works fine with excludes.
}

# Upload the zipped source code to GCS
resource "google_storage_bucket_object" "zip" {
  name   = "${var.env}-${var.function_name}-src-${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name # Use the created bucket name
  source = data.archive_file.source.output_path
}
```

This defines the packaging (`archive_file`), the GCS bucket (`google_storage_bucket`), the upload (`google_storage_bucket_object`), and the trigger (`google_cloud_scheduler_job`). It depends on resources defined in `function.tf`.

### function.tf

Defines the Pub/Sub topic and the Cloud Function resource.

```terraform title="terraform/function.tf"
# Pub/Sub Topic to trigger the function
resource "google_pubsub_topic" "main_topic" {
  name = "${var.env}-${var.function_name}"
}

# The Cloud Function resource
resource "google_cloudfunctions2_function" "main_function" {
  name     = "${var.env}-${var.function_name}"
  location = var.region
  description = "Airless function to fetch weather data from API"

  build_config {
    runtime     = "python312" # Or python310, python311, python312
    entry_point = "route"    # Matches the function name in main.py
    source {
      storage_source {
        bucket = google_storage_bucket_object.zip.bucket # Get bucket from the uploaded object
        object = google_storage_bucket_object.zip.name   # Get object name from the uploaded object
      }
    }
  }

  service_config {
    max_instance_count = 3 # Limit concurrency
    available_memory   = "256Mi"
    timeout_seconds    = 60
    # Define environment variables needed by the function and airless core/gcp libs
    environment_variables = {
      ENV                  = var.env
      LOG_LEVEL            = var.log_level
      GCP_PROJECT          = var.project_id # Airless GCP libs might need this
      GCP_REGION           = var.region     # Airless GCP libs might need this
      OPERATOR_IMPORT      = "from operator.weather import WeatherOperator"
      QUEUE_TOPIC_ERROR    = var.pubsub_topic_error_name # For base operator error routing
      # Add any other specific env vars your operator/hook might need
    }
    # ingress_settings               = "ALLOW_ALL" # Default - Allow public access if needed (not for PubSub trigger)
    # all_traffic_on_latest_revision = true
  }

  # Configure the trigger (Pub/Sub topic)
  event_trigger {
    trigger_region = var.region # Can differ from function region if needed
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.main_topic.id
    retry_policy   = "RETRY_POLICY_RETRY" # Retry on failure
  }
}

# Cloud Scheduler job to periodically trigger the function via Pub/Sub
resource "google_cloud_scheduler_job" "trigger" {
  name        = "${var.env}-${var.function_name}-trigger"
  description = "Periodically trigger the weather API function"
  schedule    = "*/15 * * * *" # Trigger every 15 minutes for demo
  time_zone   = "America/Sao_Paulo"

  pubsub_target {
    # google_pubsub_topic.main_topic is defined in function.tf
    topic_name = google_pubsub_topic.main_topic.id
    # Message payload expected by the operator's execute method
    # Example: New York City
    data = base64encode(jsonencode({
      "request_type" = "temperature",
      "lat"          = 40.7128,
      "lon"          = -74.0060
    }))
  }
}
```

This defines the `google_pubsub_topic` and the `google_cloudfunctions2_function`, linking it to the topic via `event_trigger` and configuring its source code, runtime, environment variables, and other settings.


## Deploy and Run


1.  **Initialize Terraform:**
    ```bash
    terraform init
    ```

2.  **Review Plan (Optional but Recommended):**
    ```bash
    terraform plan
    ```
    Check the output to see what resources Terraform will create.

3.  **Deploy Resources:**
    ```bash
    terraform apply
    ```
    This command will package your code, upload it, and create the GCS Bucket, Pub/Sub topic, Cloud Function, and Cloud Scheduler job on GCP. It might take a few minutes.

4.  **Test Manually (Optional):**
    You can trigger the function immediately without waiting for the scheduler:
    ```bash
    gcloud pubsub topics publish dev-weather-api --message '{"request_type": "temperature", "lat": 51.5074, "lon": -0.1278}'
    ```
    Check the Cloud Function logs in the GCP Console to see the output and verify the temperature was logged.

5.  **Monitor:** The Cloud Scheduler job is configured (by default) to trigger the function every 15 minutes. You can monitor its executions and the function logs in the GCP Console.

## Clean Up

To remove all the GCP resources created by this example, run:

```bash
terraform destroy
```
Confirm the prompt to delete the resources.
