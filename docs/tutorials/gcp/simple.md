
This quickstart guides you through installing the `airless-core` package and its GCP dependencies, setting up a basic workflow that consults a weather API and logs the response, and deploying it as a Cloud Function on Google Cloud Platform (GCP) using Terraform.

This quickstart assumes you have:

* A local IDE (VS Code, PyCharm, etc.) with Python 3.9+.
* Terminal access.
* A Google Cloud Platform account with billing enabled.
* The `gcloud` CLI installed and configured ([link](https://cloud.google.com/sdk/docs/install)).
* Terraform installed ([link](https://developer.hashicorp.com/terraform/install)).
* Core infrastructure module already defined. ([link](./core-infrastructure.md))

## Set up Local Environment & Install Airless Packages

First, set up a local Python environment to manage dependencies for developing and packaging the function source code.

=== "uv"

    ```bash
    # Create a bare virtual environment (no pyproject.toml needed for this simple example)
    uv venv .venv
    source .venv/bin/activate # Or .\venv\Scripts\activate.bat / Activate.ps1 on Windows
    # Install necessary packages
    uv pip install airless-core airless-google-cloud-core airless-google-cloud-pubsub functions-framework requests google-cloud-pubsub
    # Generate requirements.txt for Cloud Function deployment
    uv pip freeze > requirements.txt
    ```

=== "pip + venv"

    ```bash
    python -m venv .venv
    # Activate venv in Mac / Linux
    source .venv/bin/activate
    # Windows CMD: .venv\Scripts\activate.bat
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    pip install airless-core airless-google-cloud-core airless-google-cloud-pubsub functions-framework requests google-cloud-pubsub
    pip freeze > requirements.txt
    ```

## Project Structure

Create the following directory structure for your project:

```text
.
├── hook
│   └── api.py         # Code to interact with the external weather API
├── operator
│   └── weather.py     # Business logic using the hook
├── main.py            # GCP Cloud Function entry point
├── requirements.txt   # Python dependencies
├── main.tf            # Main Terraform configuration (source packaging, GCS, Scheduler)
├── function.tf        # Terraform configuration for the Cloud Function & Pub/Sub Topic
├── variables.tf       # Terraform variable definitions
├── Makefile           # Helper commands for deployment and testing
└── .env               # Environment variables (primarily for Makefile/local use)
```

Create the necessary folders and empty files:

```bash
mkdir hook operator
touch hook/api.py operator/weather.py main.py main.tf function.tf variables.tf Makefile .env
# requirements.txt should already exist from the previous step
```

## hook.py

This file defines the `ApiHook`, responsible for fetching data from the external Open-Meteo weather API. It inherits from `airless.core.hook.BaseHook`.

```python title="hook/api.py"
import requests

from airless.core.hook import BaseHook


class ApiHook(BaseHook): # (1)!
    """A simple hook to simulate fetching weather data."""

    def __init__(self):
        """Initializes the WeatherApiHook."""
        super().__init__()
        self.base_url = 'https://api.open-meteo.com/v1/forecast'

    def get_temperature(self, lat: float, lon: float) -> float:
        """
        Fetch the current temperature for a given city.

        Args:
            lat (float): The latitude of the city.
            lon (float): The longitude of the city.

        Returns:
            float: The current temperature in Celsius.

        Raises:
            requests.exceptions.RequestException: If the API request fails.
        """
        params = {
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m'
        }
        with requests.Session() as session: # (2)!
            response = session.get(
                self.base_url,
                params=params,
                timeout=10 # Add a timeout
            )
            response.raise_for_status() # (3)!
            data = response.json()
            self.logger.debug(f"Response: {data}") # (4)!

            temperature = data['current']['temperature_2m']

            return temperature

```

1.  Hooks encapsulate interactions with external systems and inherit from `BaseHook`.
2.  Using `requests.Session()` enhances performance through connection reuse and provides configuration options.
3.  `response.raise_for_status()` checks for HTTP errors (4xx, 5xx) and raises an exception if one occurred. This allows Airflow's error handling (or the base operator's error routing) to catch it.
4.  `BaseHook` provides a pre-configured logger (`self.logger`).

## operator.py

This file defines the `WeatherOperator`, which contains the core logic. It uses the `ApiHook` to fetch data and logs the result. For GCP deployment, it inherits from `airless.google.cloud.core.operator.GoogleBaseEventOperator`, which handles parsing the incoming Cloud Event.

```python title="operator/weather.py"
from airless.google.cloud.core.operator import GoogleBaseEventOperator # (1)!
from airless.core.utils import get_config # To read environment variables if needed later

from hook.api import ApiHook


class WeatherOperator(GoogleBaseEventOperator): # (2)!
    """A simple operator to fetch weather data triggered by a Cloud Event."""

    def __init__(self):
        """Initializes the WeatherOperator."""
        super().__init__()
        self.api_hook = ApiHook()

    def execute(self, data: dict, topic: str) -> None: # (3)!
        """Define which method to call based on the request type from the event data."""
        request_type = data.get('request_type') # Use .get for safer access

        if request_type == 'temperature':
            self.get_temperature(data, topic)
        else:
            # Log a warning or raise a more specific error if needed
            self.logger.critical(f"Request type '{request_type}' not implemented or missing in message data.")
            # Optionally raise an exception to trigger error handling/retry
            # raise ValueError(f"Request type '{request_type}' not implemented")

    def get_temperature(self, data: dict, topic: str) -> None:
        """Fetch the current temperature for a given city from message data."""
        lat = data.get('lat')
        lon = data.get('lon')

        if lat is None or lon is None:
            self.logger.error(f"Missing 'lat' or 'lon' in message data: {data}")
            # Decide if this should be a hard failure
            raise ValueError("Missing latitude or longitude in input data")

        try:
            temperature = self.api_hook.get_temperature(float(lat), float(lon))
            self.logger.info(f"Successfully fetched temperature for ({lat}, {lon}): {temperature}°C") # (4)!
        except Exception as e:
            self.logger.error(f"Failed to get temperature for ({lat}, {lon}): {e}")
            # Re-raise the exception to let the base operator handle error routing
            raise

```

1.  Import the base operator designed for GCP Cloud Events.
2.  Inherit from `GoogleBaseEventOperator`. This base class handles parsing the incoming `cloud_event` in `main.py` and calls the `execute` method with extracted `data` and `topic`.
3.  The `execute` method receives the payload (`data`) from the Pub/Sub message and the `topic` name.
4.  Use the built-in `self.logger` for logging. `INFO` level is often more appropriate for successful execution steps than `DEBUG`.

## main.py

This is the entry point for the GCP Cloud Function. It uses the `functions_framework` to handle the incoming Cloud Event trigger (from Pub/Sub), dynamically imports the specified operator, instantiates it, and runs it.

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

This file lists the Python dependencies needed by the Cloud Function. It's generated by `uv pip freeze` or `pip freeze`.

```text title="requirements.txt"
airless-google-cloud-core==<version>
# Add any other direct or transitive dependencies listed by freeze
```

*(Note: Replace `<version>` with the actual versions installed in your environment)*

## .env

Create a `.env` file in the root directory to store configuration, primarily for the Makefile commands. **Remember to add this file to your `.gitignore`!**

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

Fill in your `GCP_PROJECT`, `GCP_REGION`

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

## Error Handling Explanation

Airless on GCP typically utilizes a centralized error handling mechanism. The `GoogleBaseEventOperator` is designed to automatically catch uncaught exceptions that occur within your `execute` method (or methods called by it, like `api_hook.get_temperature`).

When an exception occurs, the base operator formats an error message (including the original message data, topic, and exception details) and publishes it to a designated error Pub/Sub topic. This error topic's name is configured via the `QUEUE_TOPIC_ERROR` environment variable, which we will set in the Terraform configuration (`function.tf`).

This means you generally don't need explicit `try...except` blocks for *routing* errors within your `execute` method, unless you want to perform specific cleanup or logging before letting the error propagate. The infrastructure for this error topic (and potentially a separate function to consume from it for alerts or retries) needs to exist and be specified for the main function to use. We define the `QUEUE_TOPIC_ERROR` variable in `variables.tf` and pass it to the function in `function.tf`.

## Terraform Configuration (`terraform/variables.tf`)

This file defines the input variables for your Terraform configuration, allowing for customization without changing the main code.

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

This file defines variables like project ID, region, environment name, bucket name for source code, error topic name, and function settings. Defaults are provided for convenience.

## Terraform Configuration (`terraform/main.tf`)

This file sets up the Google provider, creates the source code archive, uploads it to GCS, and defines the Cloud Scheduler job to trigger the workflow periodically.

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

## Terraform Configuration (`terraform/function.tf`)

This file defines the Pub/Sub topic that acts as the trigger and the Cloud Function resource itself.

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


## Simple Example

Only return a message to pubsub but now using GCP pubsub.
