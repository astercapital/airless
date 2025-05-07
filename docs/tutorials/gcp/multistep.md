
This quickstart guides you through deploying a workflow to Google Cloud Platform (GCP) that involves multiple steps: first, retrieving the latitude and longitude for a given city name, and second, using those coordinates to fetch the current temperature. This workflow consults two different APIs and logs the results. We will deploy this using Terraform and trigger it via Pub/Sub messages.

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
        self.weather_base_url = '[https://api.open-meteo.com/v1/forecast](https://api.open-meteo.com/v1/forecast)'
        self.geocode_base_url = '[https://geocode.xyz](https://geocode.xyz)'

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

        if request_type == 'temperature':
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
            # If you need to send results elsewhere (e.g., another Pub/Sub topic), do it here.
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

## main.py

This is the entry point for the Google Cloud Function. It uses the `functions-framework` and dynamically imports the operator specified by the `OPERATOR_IMPORT` environment variable.

```python title="main.py"
import functions_framework
import gc
import os
import importlib

# Dynamically import the operator based on environment variable
operator_import_path = os.environ.get("OPERATOR_IMPORT", "operator.weather.WeatherOperator") # (1)!
module_path, class_name = operator_import_path.rsplit('.', 1)
try:
    OperatorClass = getattr(importlib.import_module(module_path), class_name) # (2)!
except (ImportError, AttributeError) as e:
    raise ImportError(f"Could not import operator class '{class_name}' from '{module_path}': {e}")


@functions_framework.cloud_event # (3)!
def route(cloud_event):
    """
    Cloud Function entry point triggered by a Pub/Sub event.
    Instantiates the operator and runs it with the event data.
    """
    op_instance = OperatorClass() # (4)!
    op_instance.run(cloud_event) # (5)!
    gc.collect() # (6)!

```

1.  Gets the operator import path from the `OPERATOR_IMPORT` environment variable (set in Terraform), with a default.
2.  Dynamically imports the specified module and gets the operator class.
3.  Decorator indicating this function is triggered by a CloudEvent (like Pub/Sub).
4.  Instantiates the dynamically loaded operator class.
5.  Calls the `run` method (provided by the base operator) which handles the event, calls `execute`, and manages error reporting.
6.  Calls garbage collection to help manage memory in the function environment.

## requirements.txt

List the necessary Python packages for the Cloud Function.

```text title="requirements.txt"
# Replace 'your-package-name' with the actual name of your core package
airless-google-cloud-core>=0.0.4 # (1)!
requests>=2.25.0                 # (2)!
google-cloud-functions-framework>=3.0.0 # (3)!
```

1.  Your core package, specifically the GCP components (`GoogleBaseEventOperator`, `get_config`, etc.). Adjust the version as needed.
2.  The `requests` library used by the `ApiHook`.
3.  The Google Cloud Functions Framework required for the entry point.

## .env

This file is primarily used to provide variables to Terraform when running *locally*. The deployed function uses environment variables set directly in its Terraform configuration.

```dotenv title=".env"
# Used by Terraform locally via TF_VAR_... convention
TF_VAR_project_id="your-gcp-project-id" # (1)!
TF_VAR_region="us-central1"             # (2)!
TF_VAR_env="dev"                        # (3)!
# Add other TF_VAR_ variables as needed (e.g., for bucket names, error topics)
TF_VAR_function_bucket_name="your-cloud-function-source-bucket"
TF_VAR_pubsub_topic_error_name="dev-error"

# Used by local 'make trigger-*' commands (optional)
GCP_PROJECT="your-gcp-project-id"
PUBSUB_TOPIC="dev-weather-topic"
```

1.  Replace with your actual Google Cloud Project ID.
2.  Replace with the desired GCP region for deployment.
3.  Environment name (e.g., dev, staging, prod).

!!! warning
    Ensure this file is added to your `.gitignore` to avoid committing sensitive information like project IDs if applicable.

## Terraform Configuration

We'll use Terraform to define the GCP infrastructure: a Pub/Sub topic to trigger the function and the Cloud Function itself.

### variables.tf

Defines the input variables for our Terraform configuration.

```terraform title="terraform/variables.tf"
variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "Google Cloud region for deployment"
  type        = string
  default     = "us-central1"
}

variable "env" {
  description = "Deployment environment (e.g., dev, prod)"
  type        = string
  default     = "dev"
}

variable "function_bucket_name" {
  description = "Name of the GCS bucket storing function source code zip files"
  type        = string
}

variable "pubsub_topic_error_name" {
  description = "Name of the Pub/Sub topic for routing function errors"
  type        = string
}

variable "function_memory" {
  description = "Memory allocated to the Cloud Function"
  type        = string
  default     = "256Mi"
}

variable "function_timeout" {
  description = "Timeout in seconds for the Cloud Function"
  type        = number
  default     = 60 # Increased timeout for potential API calls
}

variable "function_runtime" {
  description = "Python runtime for the Cloud Function"
  type        = string
  default     = "python311" # Adjust based on your package compatibility
}

variable "source_archive_exclude" {
  description = "Set of file patterns to exclude from the source archive"
  type        = set(string)
  default     = [
    ".*",
    "*.pyc",
    "*__pycache__*",
    "terraform/*",
    "*.tf",
    ".env"
  ]
}
```

### main.tf

Configures the Terraform provider, backend (optional but recommended), and defines the process for archiving the source code.

```terraform title="terraform/main.tf"
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  # Optional: Configure remote backend (e.g., GCS) for team collaboration
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket-name"
  #   prefix = "weather-function/${var.env}"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Archive the function source code (excluding Terraform files, .env, etc.)
data "archive_file" "source_archive" {
  type        = "zip"
  source_dir  = "../" # (1)! Archive root directory containing main.py, hook/, operator/, requirements.txt
  output_path = "/tmp/weather-function-${var.env}.zip"
  excludes    = var.source_archive_exclude
}

# Upload the zipped source code to GCS
resource "google_storage_bucket_object" "source_zip" {
  name   = "source/${data.archive_file.source_archive.output_md5}.zip" # (2)! Use MD5 hash for versioning
  bucket = var.function_bucket_name
  source = data.archive_file.source_archive.output_path

  depends_on = [data.archive_file.source_archive]
}

```

1.  `source_dir` points to the parent directory (`../`) relative to the `terraform` folder, capturing `main.py`, `hook/`, `operator/`, and `requirements.txt`.
2.  The object name includes the MD5 hash of the archive content, ensuring Terraform uploads a new version only when the code changes.

### function.tf

Defines the Pub/Sub topic and the Cloud Function resource.

```terraform title="terraform/function.tf"
# Pub/Sub topic to trigger the function
resource "google_pubsub_topic" "weather_topic" {
  name = "${var.env}-weather-topic" # (1)! Topic name includes environment
}

# Cloud Function resource
resource "google_cloudfunctions2_function" "weather_function" {
  name     = "${var.env}-weather-function" # (2)! Function name includes environment
  location = var.region
  project  = var.project_id

  description = "Fetches weather data based on city or coordinates via Pub/Sub trigger"

  build_config {
    runtime     = var.function_runtime
    entry_point = "route" # Matches the function name in main.py
    source {
      storage_source {
        bucket = var.function_bucket_name
        object = google_storage_bucket_object.source_zip.name # (3)! Points to the uploaded zip
      }
    }
  }

  service_config {
    max_instance_count = 5 # Adjust as needed
    available_memory   = var.function_memory
    timeout_seconds    = var.function_timeout
    environment_variables = { # (4)! Environment variables for the function
      ENV                   = var.env
      LOG_LEVEL             = "INFO" # Or DEBUG for more verbose logs
      GCP_PROJECT           = var.project_id
      GCP_REGION            = var.region
      OPERATOR_IMPORT       = "operator.weather.WeatherOperator" # Path to your operator class
      QUEUE_TOPIC_ERROR     = var.pubsub_topic_error_name # Topic for error routing
      # Add any other necessary env vars your operator/hook might need
    }
    # Optional: Configure VPC connector, service account, etc.
    # service_account_email = "your-service-account@your-project-id.iam.gserviceaccount.com"
  }

  event_trigger { # (5)! Configure the Pub/Sub trigger
    trigger_region = var.region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.weather_topic.id
    retry_policy   = "RETRY_POLICY_RETRY" # Retry on failure
  }

  depends_on = [
    google_storage_bucket_object.source_zip,
    google_pubsub_topic.weather_topic
  ]
}

# Optional: Grant Pub/Sub permission to invoke the function if needed
# (often handled automatically or via default service accounts, but good to be aware)
# resource "google_cloudfunctions2_function_iam_member" "invoker" {
#   project        = google_cloudfunctions2_function.weather_function.project
#   location       = google_cloudfunctions2_function.weather_function.location
#   cloud_function = google_cloudfunctions2_function.weather_function.name
#   role           = "roles/cloudfunctions.invoker"
#   member         = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com" # Replace project_number
# }

# resource "google_project_iam_member" "pubsub_token_creator" {
#   project = var.project_id
#   role    = "roles/iam.serviceAccountTokenCreator"
#   member  = "serviceAccount:service-${var.project_number}@gcp-sa-pubsub.iam.gserviceaccount.com" # Replace project_number
# }

```

1.  Defines the Pub/Sub topic that will receive messages to trigger the workflow.
2.  Defines the Cloud Function resource.
3.  Specifies the GCS location of the zipped source code uploaded by `main.tf`.
4.  Sets crucial environment variables used by `main.py` and the operator/hooks (via `get_config`). This replaces the local `.env` for the deployed function.
5.  Configures the function to be triggered by messages published to `google_pubsub_topic.weather_topic`.

## Makefile

The Makefile helps automate Terraform actions and provides commands to trigger the deployed function by publishing messages to Pub/Sub.

```makefile title="Makefile"
# Default environment variables (can be overridden)
ENV ?= dev
GCP_PROJECT ?= $(shell grep 'TF_VAR_project_id' .env | cut -d '=' -f2 | tr -d '"')
GCP_REGION ?= $(shell grep 'TF_VAR_region' .env | cut -d '=' -f2 | tr -d '"')
PUBSUB_TOPIC ?= $(ENV)-weather-topic

# Terraform commands
tf-init:
	@echo "+++ Initializing Terraform in $(ENV) environment..."
	@cd terraform && terraform init

tf-plan: tf-init
	@echo "+++ Planning Terraform changes for $(ENV) environment..."
	@cd terraform && terraform plan -var-file=../.env -var="env=$(ENV)"

tf-apply: tf-init
	@echo "+++ Applying Terraform changes for $(ENV) environment..."
	@cd terraform && terraform apply -auto-approve -var-file=../.env -var="env=$(ENV)"

tf-destroy: tf-init
	@echo "+++ Destroying Terraform resources for $(ENV) environment..."
	@cd terraform && terraform destroy -auto-approve -var-file=../.env -var="env=$(ENV)"

# --- Function Trigger Commands ---

# Trigger function to get temperature for specific coordinates
trigger-temp:
	@echo "+++ Triggering temperature request for $(ENV)..."
	@gcloud pubsub topics publish $(PUBSUB_TOPIC) \
		--project $(GCP_PROJECT) \
		--message '{"request_type": "temperature", "lat": 40.7128, "lon": -74.0060}' # (1)!

# Trigger function to get lat/long for a city
trigger-latlong:
	@echo "+++ Triggering lat/long request for $(ENV)..."
	@gcloud pubsub topics publish $(PUBSUB_TOPIC) \
		--project $(GCP_PROJECT) \
		--message '{"request_type": "city_lat_long", "city_name": "New York"}' # (2)!

.PHONY: tf-init tf-plan tf-apply tf-destroy trigger-temp trigger-latlong

```

??? Warning
    Makefile indentation must use tabs, not spaces.

1.  Publishes a JSON message to the configured Pub/Sub topic to request the temperature.
2.  Publishes a JSON message to the configured Pub/Sub topic to request the latitude and longitude.

## Deploy and Run

1.  **Set up Prerequisites:**
    * Install [Terraform](https://developer.hashicorp.com/terraform/downloads).
    * Install [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`).
    * Authenticate `gcloud`: `gcloud auth login` and `gcloud auth application-default login`.
    * Configure `gcloud` project: `gcloud config set project your-gcp-project-id`.
    * Create the GCS bucket specified in `.env` for `TF_VAR_function_bucket_name`.
    * Ensure the Pub/Sub topic specified in `.env` for `TF_VAR_pubsub_topic_error_name` exists, or create it (e.g., `gcloud pubsub topics create dev-error`).

2.  **Fill in `.env`:** Update the placeholder values in the `.env` file with your actual project ID, desired region, environment name, function source bucket, and error topic.

3.  **Deploy Infrastructure:**
    ```bash
    make tf-apply ENV=dev # Or your desired environment name
    ```
    This command will initialize Terraform, plan the changes, and apply them to create the Pub/Sub topic and Cloud Function in your GCP project.

4.  **Run the Workflow:** Trigger the function by publishing messages using the Makefile targets:

    * To get coordinates for a city (e.g., New York):
        ```bash
        make trigger-latlong ENV=dev
        ```

    * To get the temperature for specific coordinates (e.g., New York's approx. coordinates):
        ```bash
        make trigger-temp ENV=dev
        ```

5.  **Check Logs:** View the function's logs in the Google Cloud Console (Logging > Logs Explorer) by filtering for your Cloud Function resource (`${ENV}-weather-function`). You should see log output showing the API calls and the results (coordinates or temperature), or error messages routed to the error topic if something went wrong.
