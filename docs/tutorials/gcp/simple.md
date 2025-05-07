
This quickstart guides you through installing the `airless-core` package and its GCP dependencies, setting up a basic workflow that consults a weather API and logs the response, and deploying it as a Cloud Function on Google Cloud Platform (GCP) using Terraform.

This quickstart assumes you have:

* A local IDE (VS Code, PyCharm, etc.) with Python 3.9+.
* Terminal access.
* A Google Cloud Platform account with billing enabled.
* The `gcloud` CLI installed and configured ([link](https://cloud.google.com/sdk/docs/install)).
* Terraform installed ([link](https://developer.hashicorp.com/terraform/install)).

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
        self.base_url = '[https://api.open-meteo.com/v1/forecast](https://api.open-meteo.com/v1/forecast)'

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
            self.logger.warning(f"Request type '{request_type}' not implemented or missing in message data.")
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
import gc
import os # Import os to read environment variables

from airless.core.utils import get_config

# Dynamically import the operator specified in the environment variable
# This allows reusing this entry point for different functions
operator_import_path = get_config("OPERATOR_IMPORT", "from operator.weather import WeatherOperator") # Provide default
exec(f'{operator_import_path} as op') # (1)!

@functions_framework.cloud_event # (2)!
def route(cloud_event):
    """
    GCP Cloud Function entry point triggered by a Cloud Event (e.g., Pub/Sub).

    Args:
        cloud_event: The Cloud Event object representing the trigger.
                     Contains metadata and the message payload (base64 encoded).
    """
    try:
        instance = op() # Instantiate the operator
        instance.run(cloud_event) # (3)! The base operator handles event parsing and calls execute
    except Exception as e:
        # Although the base operator handles error *routing*, log entry point failure
        print(f"ERROR: Function execution failed at entry point: {e}") # Use print as logger might not be set up yet
        # Re-raise to ensure GCP marks the function execution as failed
        raise
    finally:
        gc.collect() # Suggest garbage collection
```

1.  `exec(f'{operator_import_path} as op')` dynamically imports the operator class based on the `OPERATOR_IMPORT` environment variable (defined in Terraform). This makes the `main.py` reusable.
2.  `@functions_framework.cloud_event` decorator registers this function to handle Cloud Events.
3.  `instance.run(cloud_event)` is called. The `GoogleBaseEventOperator`'s `run` method parses the `cloud_event` (decoding the Pub/Sub message data) and then calls the `execute` method you defined in `WeatherOperator` with the extracted `data` and `topic`.

## requirements.txt

This file lists the Python dependencies needed by the Cloud Function. It's generated by `uv pip freeze` or `pip freeze`.

```text title="requirements.txt"
airless-core==<version>
airless-google-cloud-core==<version>
airless-google-cloud-pubsub==<version>
functions-framework==<version>
google-cloud-pubsub==<version>
requests==<version>
# Add any other direct or transitive dependencies listed by freeze
```

*(Note: Replace `<version>` with the actual versions installed in your environment)*

## Error Handling Explanation

Airless on GCP typically utilizes a centralized error handling mechanism. The `GoogleBaseEventOperator` is designed to automatically catch uncaught exceptions that occur within your `execute` method (or methods called by it, like `api_hook.get_temperature`).

When an exception occurs, the base operator formats an error message (including the original message data, topic, and exception details) and publishes it to a designated error Pub/Sub topic. This error topic's name is configured via the `QUEUE_TOPIC_ERROR` environment variable, which we will set in the Terraform configuration (`function.tf`).

This means you generally don't need explicit `try...except` blocks for *routing* errors within your `execute` method, unless you want to perform specific cleanup or logging before letting the error propagate. The infrastructure for this error topic (and potentially a separate function to consume from it for alerts or retries) needs to exist and be specified for the main function to use. We define the `QUEUE_TOPIC_ERROR` variable in `variables.tf` and pass it to the function in `function.tf`.

## Terraform Configuration (`variables.tf`)

This file defines the input variables for your Terraform configuration, allowing for customization without changing the main code.

```terraform title="variables.tf"
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

variable "operator_import_path" {
  description = "Python import path for the operator in main.py."
  type        = string
  default     = "from operator.weather import WeatherOperator"
}

variable "function_name" {
  description = "Base name for the Cloud Function."
  type        = string
  default     = "weather-api"
}

variable "function_memory" {
  description = "Memory allocation for the Cloud Function."
  type        = string
  default     = "256Mi"
}

variable "function_timeout" {
  description = "Timeout in seconds for the Cloud Function."
  type        = number
  default     = 60 # Increased timeout for potential API calls
}

variable "scheduler_schedule" {
  description = "Cron schedule for the Cloud Scheduler trigger."
  type        = string
  default     = "*/15 * * * *" # Trigger every 15 minutes for demo
}

variable "scheduler_timezone" {
  description = "Timezone for the Cloud Scheduler trigger."
  type        = string
  default     = "America/Sao_Paulo"
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

## Terraform Configuration (`main.tf`)

This file sets up the Google provider, creates the source code archive, uploads it to GCS, and defines the Cloud Scheduler job to trigger the workflow periodically.

```terraform title="main.tf"
provider "google" {
  project = var.project_id
  region  = var.region
}

# Archive the source code directory into a zip file
data "archive_file" "source" {
  type        = "zip"
  source_dir  = "${path.module}/" # Zips the current directory
  output_path = "/tmp/${var.env}-${var.function_name}-source.zip"
  excludes    = var.source_archive_exclude

  # Include necessary files/dirs explicitly if source_dir is broader
  # For this structure, source_dir = "." works fine with excludes.
}

# Ensure the GCS bucket for source code exists
# If you manage the bucket elsewhere, remove this and just use the var.function_bucket_name
resource "google_storage_bucket" "function_source_bucket" {
  name                        = var.function_bucket_name
  location                    = var.region
  uniform_bucket_level_access = true

  # Optional: Add lifecycle rules, etc.
}

# Upload the zipped source code to GCS
resource "google_storage_bucket_object" "zip" {
  name   = "${var.env}-${var.function_name}-src-${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.function_source_bucket.name # Use the created bucket name
  source = data.archive_file.source.output_path

  depends_on = [
    data.archive_file.source,
    google_storage_bucket.function_source_bucket # Ensure bucket exists before upload
  ]
}

# Cloud Scheduler job to periodically trigger the function via Pub/Sub
resource "google_cloud_scheduler_job" "trigger" {
  name        = "${var.env}-${var.function_name}-trigger"
  description = "Periodically trigger the weather API function"
  schedule    = var.scheduler_schedule
  time_zone   = var.scheduler_timezone

  pubsub_target {
    # google_pubsub_topic.main_topic is defined in function.tf
    topic_name = google_pubsub_topic.main_topic.id
    # Message payload expected by the operator's execute method
    data = base64encode(jsonencode({
      request_type = "temperature",
      lat          = 40.7128, # Example: New York City
      lon          = -74.0060
    }))
  }

  depends_on = [
    google_pubsub_topic.main_topic # Ensure topic exists before scheduling job
  ]
}

# Output the function URL (if needed, though it's event-driven)
output "cloud_function_uri" {
  description = "The URI of the deployed Cloud Function."
  value       = google_cloudfunctions2_function.main_function.service_config[0].uri
  sensitive   = true # URIs can sometimes be sensitive
}

output "pubsub_topic_name" {
  description = "The name of the Pub/Sub topic triggering the function."
  value       = google_pubsub_topic.main_topic.id
}

output "scheduler_job_name" {
  description = "The name of the Cloud Scheduler job."
  value       = google_cloud_scheduler_job.trigger.name
}
```

This defines the packaging (`archive_file`), the GCS bucket (`google_storage_bucket`), the upload (`google_storage_bucket_object`), and the trigger (`google_cloud_scheduler_job`). It depends on resources defined in `function.tf`.

## Terraform Configuration (`function.tf`)

This file defines the Pub/Sub topic that acts as the trigger and the Cloud Function resource itself.

```terraform title="function.tf"
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
    runtime     = "python39" # Or python310, python311, python312
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
    available_memory   = var.function_memory
    timeout_seconds    = var.function_timeout
    # Define environment variables needed by the function and airless core/gcp libs
    environment_variables = {
      ENV                  = var.env
      LOG_LEVEL            = var.log_level
      GCP_PROJECT          = var.project_id # Airless GCP libs might need this
      GCP_REGION           = var.region     # Airless GCP libs might need this
      OPERATOR_IMPORT      = var.operator_import_path
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

  # Ensure the source code is uploaded before creating the function
  depends_on = [
    google_storage_bucket_object.zip,
    google_pubsub_topic.main_topic
  ]
}
```

This defines the `google_pubsub_topic` and the `google_cloudfunctions2_function`, linking it to the topic via `event_trigger` and configuring its source code, runtime, environment variables, and other settings.

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

# Replace with your desired GCP Region
GCP_REGION="us-central1"

# --- Terraform Variable Defaults (or overrides) ---
# Bucket must be globally unique or match an existing one you own
FUNCTION_BUCKET_NAME="your-unique-bucket-name-for-functions"

# Optional: Override default names if needed
# FUNCTION_NAME="weather-api"
# TOPIC_NAME="dev-weather-api"
# SCHEDULER_NAME="dev-weather-api-trigger"
# PUBSUB_TOPIC_ERROR="dev-airless-error"

# --- Operator Import ---
# Matches the default in variables.tf
OPERATOR_IMPORT="from operator.weather import WeatherOperator"

# --- Variables derived from Terraform outputs (used by 'make trigger') ---
# These will be dynamically populated if needed or can be fetched manually
# FULL_TOPIC_NAME="projects/your-gcp-project-id/topics/dev-weather-api"
```

Fill in your `GCP_PROJECT`, `GCP_REGION`, and a unique `FUNCTION_BUCKET_NAME`.

## Makefile

Create a `Makefile` to simplify deployment and testing commands.

!!! warning "Makefile Indentation"
    Remember that Makefiles use **tabs** for indentation, not spaces.

```makefile title="Makefile"
# Load environment variables from .env file
# Ensure .env exists and has values for GCP_PROJECT, GCP_REGION, TOPIC_NAME etc.
include .env
export $(shell sed 's/=.*//' .env)

# Use variables defined in .env
PROJECT_ID := $(GCP_PROJECT)
REGION := $(GCP_REGION)
ENV_NAME := $(ENV)
FUNCTION := $(ENV_NAME)-$(FUNCTION_NAME) # Construct full function name if needed later
TOPIC := $(ENV_NAME)-$(shell echo $(FUNCTION_NAME) | sed 's/_/-/g') # Construct topic name based on convention in function.tf
FULL_TOPIC_NAME := projects/$(PROJECT_ID)/topics/$(TOPIC) # Construct full topic path

.PHONY: help init plan deploy destroy trigger clean

help:
	@echo "Available commands:"
	@echo "  init      - Initialize Terraform"
	@echo "  plan      - Create Terraform execution plan"
	@echo "  deploy    - Apply Terraform changes (deploy/update resources)"
	@echo "  destroy   - Destroy Terraform-managed resources"
	@echo "  trigger   - Publish a test message to the Pub/Sub topic"
	@echo "  clean     - Remove temporary Terraform files"

init:
	@echo "Initializing Terraform..."
	@terraform init

plan:
	@echo "Planning Terraform deployment..."
	@terraform plan \
		-var="project_id=$(PROJECT_ID)" \
		-var="region=$(REGION)" \
		-var="env=$(ENV_NAME)" \
		-var="function_bucket_name=$(FUNCTION_BUCKET_NAME)" \
		# Add other -var flags if needed to override tfvars or defaults

deploy: init
	@echo "Deploying resources with Terraform..."
	@terraform apply -auto-approve \
		-var="project_id=$(PROJECT_ID)" \
		-var="region=$(REGION)" \
		-var="env=$(ENV_NAME)" \
		-var="function_bucket_name=$(FUNCTION_BUCKET_NAME)" \
		# Add other -var flags if needed

destroy:
	@echo "Destroying resources with Terraform..."
	@read -p "Are you sure you want to destroy all resources? [y/N] " confirm && [[ $$confirm == [yY] || $$confirm == [yY][eE][sS] ]] || exit 1
	@terraform destroy -auto-approve \
		-var="project_id=$(PROJECT_ID)" \
		-var="region=$(REGION)" \
		-var="env=$(ENV_NAME)" \
		-var="function_bucket_name=$(FUNCTION_BUCKET_NAME)" \
		# Add other -var flags if needed

trigger:
	@echo "Publishing test message to topic: $(FULL_TOPIC_NAME)"
	@gcloud pubsub topics publish $(FULL_TOPIC_NAME) \
		--message '{"request_type": "temperature", "lat": 51.5074, "lon": -0.1278}' # Example: London

clean:
	@echo "Cleaning up Terraform files..."
	@rm -rf .terraform .terraform.lock.hcl /tmp/$(ENV_NAME)-$(FUNCTION_NAME)-source.zip

```

This Makefile provides convenient targets:

* `make init`: Initializes Terraform.
* `make plan`: Shows the Terraform execution plan.
* `make deploy`: Deploys or updates the GCP resources.
* `make destroy`: Removes the GCP resources created by Terraform.
* `make trigger`: Sends a sample message directly to the Pub/Sub topic to test the function independently of the scheduler.
* `make clean`: Removes local Terraform state files and the temporary zip archive.

## Deploy and Run

1.  **Initialize Terraform:**
    ```bash
    make init
    ```

2.  **Review Plan (Optional but Recommended):**
    ```bash
    make plan
    ```
    Check the output to see what resources Terraform will create.

3.  **Deploy Resources:**
    ```bash
    make deploy
    ```
    This command will package your code, upload it, and create the GCS Bucket, Pub/Sub topic, Cloud Function, and Cloud Scheduler job on GCP. It might take a few minutes.

4.  **Test Manually (Optional):**
    You can trigger the function immediately without waiting for the scheduler:
    ```bash
    make trigger
    ```
    Check the Cloud Function logs in the GCP Console to see the output and verify the temperature was logged.

5.  **Monitor:** The Cloud Scheduler job is configured (by default) to trigger the function every 15 minutes. You can monitor its executions and the function logs in the GCP Console.

## Clean Up

To remove all the GCP resources created by this example, run:

```bash
make destroy
```
Confirm the prompt to delete the resources.


## Simple Example

Only return a message to pubsub but now using GCP pubsub.

Quais precisa criar

- Exemplo subindo o erro do GCP com o terraform e mensagem simples
- Exemplo subindo o erro e email do GCP com o terraform pegando uma mensagem e mandando uma notificação por email
- Exemplo subindo o erro e email do GCP com o terraform pegando uma mensagem, salvando no lake e mandando uma notificação por email
- Exemplo subindo o erro e redirect do GCP com o terraform pegando uma mensagem e fazendo um map para o mesmo topic com outro request type e salvando no datalake no final
- Exemplo subindo o erro e delay do GCP com o terraform pegando uma mensagem e fazendo delay para o mesmo topic com outro request type e salvando no datalake no final
