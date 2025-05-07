## Building Airless Core Infrastructure on GCP with Terraform

This guide explains how to set up the essential GCP resources for an Airless workflow orchestrator using Terraform. Airless leverages serverless functions and message queues to create scalable, event-driven workflows.

### Why Use Google Cloud Functions in Airless?

Airless is designed around a serverless, event-driven architecture. Google Cloud Functions are a natural fit for this model in GCP for several reasons outlined in the Airless philosophy:

1.  **Serverless:** Cloud Functions eliminate the need to manage underlying servers or infrastructure. You only pay for execution time, which is cost-effective, especially for workflows that aren't running constantly. This aligns with Airless's goal to avoid the fixed costs and management overhead of traditional orchestrators like a dedicated Airflow instance.
2.  **Scalability:** Cloud Functions automatically scale based on the incoming event load (e.g., messages in a Pub/Sub topic). This handles the "massive parallel processing" requirement mentioned for Airless, particularly for use cases like data scraping where the number of tasks can vary dramatically and unpredictably.
3.  **Event-Driven:** Functions are triggered by events, such as messages published to a Pub/Sub topic or HTTP requests. This fits perfectly with Airless's data flow where tasks trigger subsequent tasks by publishing messages.
4.  **Decoupling:** Using functions triggered by queues (Pub/Sub) decouples different stages of a workflow. Each function performs a specific task and communicates with others via messages, enhancing resilience and modularity.

### Why Use Terraform?

Terraform is an Infrastructure as Code (IaC) tool used to define and provision infrastructure resources across various cloud providers, including GCP. Using Terraform for Airless offers significant advantages:

1.  **Reproducibility & Consistency:** Define your entire Airless infrastructure (Functions, Pub/Sub topics, Storage Buckets, etc.) in configuration files. This ensures you can create identical environments (dev, staging, prod) consistently.
2.  **Version Control:** Store your infrastructure configuration in version control systems (like Git). Track changes, collaborate with others, and roll back to previous states if needed.
3.  **Automation:** Automate the provisioning and management of your GCP resources, reducing manual effort and the potential for human error.
4.  **Modularity:** Break down your infrastructure into reusable modules (as demonstrated in the provided code), making configurations easier to manage and scale.
5.  **State Management:** Terraform keeps track of the resources it manages in a state file, allowing it to understand dependencies and manage updates or deletions safely.

### The Need for `_raw` Storage

In data processing pipelines like those often built with Airless, it's crucial to have intermediate storage layers. The `_raw` storage bucket (e.g., `${var.env}-aster-data-platform-raw` in `storage.tf`) serves several key purposes:

1.  **Error Handling & Debugging:** When a function fails processing a message, the original message data and error details can be stored in the `_raw` bucket (or a dedicated error location). This prevents data loss and allows for later analysis and reprocessing. The Error function often coordinates this.
2.  **Data Staging:** Functions might fetch data that needs to be temporarily stored before being processed by a subsequent task or loaded into a final destination. The `_raw` or `_landing_tmp` buckets act as these staging areas.
3.  **Auditing & Compliance:** Storing raw incoming data or intermediate results can be necessary for auditing or compliance purposes.
4.  **Decoupling Processing:** Allows tasks to deposit data without needing immediate processing by the next step, further decoupling the workflow.

The provided `storage.tf` also includes lifecycle rules to transition older data to cheaper storage classes (like ARCHIVE), managing costs effectively.

### Terraform Module Structure

The provided Terraform code is structured as a **module**. This is a best practice in Terraform that promotes reusability and organization. A module is a self-contained package of Terraform configurations that manages a set of related resources.

* **Inputs:** The module defines input variables (`variables.tf`) like `project_id`, `region`, `env`, `error_config`, etc. This allows users of the module to customize the deployment without modifying the core code.
* **Resources:** The module contains the resource definitions (`.tf` files like `error.tf`, `delay.tf`, `storage.tf`, etc.) that create the actual infrastructure (Cloud Functions, Pub/Sub topics, GCS buckets).
* **Outputs:** The module defines outputs (`output.tf`) like bucket names and Pub/Sub topic names/IDs. These outputs expose key information about the created resources, which can be used by other Terraform configurations or for reference.

By using a module, you can easily deploy this core Airless infrastructure multiple times (e.g., for different environments or projects) with different configurations by simply calling the module and providing the appropriate input variables.

### Terraform Project Setup (`backend.tf`, etc.)

When using Terraform, you typically organize your code into several files. While the provided code represents a module, a typical Terraform project using this module would also include:

1.  **`main.tf` (Root):** This file would define the provider (Google Cloud) and call the Airless core module, passing the required input variables.
2.  **`variables.tf` (Root):** Defines variables for the root configuration (potentially passing them down to the module).
3.  **`outputs.tf` (Root):** Defines outputs for the overall deployment (potentially exposing module outputs).
4.  **`backend.tf`:** This crucial file configures Terraform's state management. It tells Terraform where to store the state file, which tracks the resources managed by the configuration. Using a remote backend (like a GCS bucket) is highly recommended for collaboration and consistency.

??? Example "Example `backend.tf` and Root `main.tf`"

    **`backend.tf`**
    ```terraform
    terraform {
      backend "gcs" {
        bucket = "your-terraform-state-bucket-name" # Needs to be created beforehand
        prefix = "airless/core/dev"                 # Path within the bucket for this state
      }
    }
    ```

    **Root `main.tf`**
    ```terraform
    provider "google" {
      project = var.project_id
      region  = var.region
    }

    resource "google_storage_bucket" "function_code_bucket" {
      name     = "${var.env}-airless-function-code"
      location = var.region
    }

    # Example of creating a topic needed by the error function
    resource "google_pubsub_topic" "pubsub_to_bq" {
      name = "${var.env}-pubsub-to-bq"
    }

    module "airless_core" {
      source = "./modules/airless-core" # Or path/URL to your module

      project_id = var.project_id
      region     = var.region
      env        = var.env
      log_level  = var.log_level

      function_bucket = {
        id   = google_storage_bucket.function_code_bucket.id
        name = google_storage_bucket.function_code_bucket.name
      }

      queue_topic_pubsub_to_bq = {
        id   = google_pubsub_topic.pubsub_to_bq.id
        name = google_pubsub_topic.pubsub_to_bq.name
      }

      source_archive_exclude = [
        ".*",
        "__pycache__",
        "*.pyc"
      ]

      error_config = {
        bigquery = {
          dataset = "airless_logs"
          table   = "errors"
        }
        email = {
          sender     = "noreply@example.com"
          recipients = ["alerts-dev@example.com"]
        }
        slack = {
          channels = ["#airless-alerts-dev"]
        }
      }
    }
    ```

### Core Function Importance

The Airless core infrastructure includes several specialized functions. Their importance generally follows this hierarchy:

1.  **Error Function (`error.tf`):** This is arguably the **most critical** function. It acts as a centralized sink for all errors occurring in other functions. Its responsibilities include logging the error details (potentially to BigQuery via another queue/function and the `_raw` bucket), implementing retry logic (potentially using the Delay function), and triggering notifications. Without robust error handling, workflows become brittle and prone to data loss.
2.  **Delay Function (`delay.tf`) & Redirect Function (`redirect.tf`):** These enable core workflow patterns.
    * **Delay:** Allows introducing controlled pauses in a workflow (e.g., for rate limiting, waiting for external processes, or implementing exponential backoff for retries directed by the Error function).
    * **Redirect:** Enables fanning out tasks. A single message can be duplicated and sent to multiple different downstream topics/functions, facilitating parallel processing and complex branching logic.
3.  **Email (`email.tf`) & Slack (`slack.tf`) Notification Functions:** These are primarily for monitoring and alerting. While important for operational visibility, the core workflow can often function without them (though you wouldn't know if something went wrong!). They decouple the notification logic (SMTP details, Slack API tokens) from the business logic functions, making the system cleaner. They are often triggered by the Error function or at specific success/milestone points in a workflow.

## Terraform Code for Airless Core Infrastructure

Below is the Terraform code based on the files you provided, structured as a module, along with explanations.

**Assumed File Structure for the Module:**

```
modules/
└── airless-core/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── storage.tf
    ├── error.tf
    ├── delay.tf
    ├── redirect.tf
    ├── email.tf
    ├── slack.tf
    └── function/       # Directory containing function source
        └── core/
            ├── main.py
            └── requirements.txt
            └── ... # Other Python code/dependencies
```

---

**`variables.tf`**

* Defines the inputs required by the module. This makes the module configurable.
* Includes essential parameters like GCP `project_id`, `region`, `env` (environment name like 'dev' or 'prod'), `log_level`, buckets for function code and data (`function_bucket`, implicitly created `aster_data_platform_*`), error handling configuration (`error_config`), and dependencies like external queues (`queue_topic_pubsub_to_bq`).

```terraform
# modules/airless-core/variables.tf

variable "project_id" {
  description = "GCP Project ID where resources will be deployed."
  type        = string
}

variable "region" {
  description = "GCP Region to create the resources in."
  type        = string
}

variable "env" {
  description = "Deployment environment (e.g., 'dev', 'staging', 'prod'). Used as a prefix for resource names."
  type        = string
}

variable "log_level" {
  description = "Default log level for Cloud Functions (e.g., 'DEBUG', 'INFO', 'WARNING')."
  type        = string
  default     = "INFO"
}

variable "function_bucket" {
  description = "Bucket object containing the ID and name for storing Cloud Function source code zip files."
  type = object({
    id   = string
    name = string
  })
}

variable "queue_topic_pubsub_to_bq" {
  description = "Pub/Sub topic object (id, name) used by the Error function to send structured error logs, potentially to a BigQuery sink."
  type = object({
    id   = string
    name = string
  })
}

variable "source_archive_exclude" {
  description = "Set of file patterns to exclude when creating the function source code zip archive."
  type        = set(string)
  default = [
    ".*",
    "__pycache__",
    "*.pyc"
  ]
}

variable "error_config" {
  description = "Configuration for error handling, including BigQuery logging, email, and Slack notifications."
  type = object({
    bigquery = object({
      dataset = string
      table   = string
    })
    email = object({
      sender     = string
      recipients = list(string)
    })
    slack = object({
      channels = list(string)
    })
  })
}
```

---

**`main.tf`**

* This file handles the packaging and uploading of the Cloud Function source code.
* `data "archive_file" "source_core"`: Zips the contents of the `../function/core` directory (relative to this `main.tf` file). It excludes files matching patterns in `var.source_archive_exclude`. The `output_path` is a temporary location for the zip file.
* `resource "google_storage_bucket_object" "zip_core"`: Uploads the generated zip file (`data.archive_file.source_core.output_path`) to the GCS bucket specified by `var.function_bucket.name`. The object name includes the MD5 hash of the zip file (`data.archive_file.source_core.output_md5`) to ensure that changes in the source code result in a new object, triggering function updates.

```terraform
# modules/airless-core/main.tf

data "archive_file" "source_core" {
  type        = "zip"
  # Assumes your Python code for the core functions is in ./function/core/
  source_dir  = "${path.module}/function/core"
  output_path = "/tmp/function-core-${var.env}.zip" # Use a unique temp path
  excludes    = var.source_archive_exclude
}

resource "google_storage_bucket_object" "zip_core" {
  source       = data.archive_file.source_core.output_path
  content_type = "application/zip"
  # Name includes hash to trigger updates when code changes
  name         = "src/core-${data.archive_file.source_core.output_md5}.zip"
  bucket       = var.function_bucket.name

  # Ensure the archive is created before trying to upload
  depends_on = [
    data.archive_file.source_core
  ]
}
```

*Note: Ensure the `function/core` directory exists adjacent to your module's `.tf` files and contains `main.py`, `requirements.txt`, and any other necessary Python code.*

**`function/core/main.py`** (Example Entry Point)

* This Python code is the entry point for *all* the core Cloud Functions defined in this module.
* It uses an environment variable `OPERATOR_IMPORT` (set in the Terraform resource definitions) to dynamically import the correct Airless operator class for the specific function (e.g., `GoogleErrorReprocessOperator`, `GoogleDelayOperator`).
* The `route` function is triggered by the Cloud Event (e.g., Pub/Sub message) and calls the `run` method of the dynamically loaded operator instance.
* `gc.collect()` helps manage memory in the serverless environment.

```python
# modules/airless-core/function/core/main.py

import functions_framework
import gc
import os
import importlib

# Dynamically import the operator based on environment variable
operator_import_path = os.environ.get("OPERATOR_IMPORT", "")
if not operator_import_path:
    raise ValueError("OPERATOR_IMPORT environment variable not set.")

try:
    # Example: "from airless.google.cloud.core.operator import GoogleDelayOperator"
    # Extracts module path and class name
    parts = operator_import_path.split(" import ")
    from_path = parts[0].replace("from ", "")
    class_name = parts[1]

    # Import the module and get the class
    module = importlib.import_module(from_path)
    OperatorClass = getattr(module, class_name)

except (ImportError, AttributeError, IndexError, ValueError) as e:
    raise ImportError(f"Could not import operator from '{operator_import_path}': {e}")


@functions_framework.cloud_event
def route(cloud_event):
    """
    Cloud Function entry point triggered by a Pub/Sub event.
    Dynamically routes the event to the appropriate Airless operator.
    """
    # Instantiate the dynamically loaded operator class
    operator_instance = OperatorClass()
    # Run the operator with the incoming event data
    operator_instance.run(cloud_event)
    # Explicitly run garbage collection
    gc.collect()

```

**`function/core/requirements.txt`** (Example Dependencies)

* Lists the Python packages required by the core functions. These will be installed when GCP builds the function environment.

```text
# modules/airless-core/function/core/requirements.txt
functions-framework>=3.0.0 # Required by GCP for Python functions
google-cloud-pubsub>=2.0.0
google-cloud-storage>=2.0.0
google-cloud-secret-manager>=2.0.0
# Add the specific airless packages needed by the core operators
airless-core~=0.1.5
airless-google-cloud-core~=0.0.4
airless-google-cloud-secret-manager~=0.0.4
airless-google-cloud-storage~=0.0.7
airless-google-cloud-bigquery~=0.0.5 # Likely needed by error operator
airless-slack~=0.0.5
airless-email~=0.0.6

```

---

**`storage.tf`**

* Defines the Google Cloud Storage (GCS) buckets.
* `google_storage_bucket`: Creates buckets for different data stages:
    * `landing_tmp`: Temporary area.
    * `raw`: For storing raw/error data, potentially with lifecycle rules.
    * `landing`: Main landing zone for incoming data.
* `lifecycle_rule`: Automatically manages objects in the bucket (e.g., moves objects older than 30 days to ARCHIVE storage class to save costs).
* `force_destroy = false`: A safety measure to prevent accidental deletion of buckets containing data when running `terraform destroy`. Set to `true` only for temporary/test buckets.

```terraform
# modules/airless-core/storage.tf

resource "google_storage_bucket" "aster_data_platform_landing_tmp" {
  project       = var.project_id
  name          = "${var.env}-aster-data-platform-landing-tmp"
  location      = var.region
  force_destroy = false # Set to true only for non-production environments if needed

  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "aster_data_platform_raw" {
  project       = var.project_id
  name          = "${var.env}-aster-data-platform-raw"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  # Example Lifecycle Rule: Move data to Archive after 30 days
  lifecycle_rule {
    condition {
      age = 30 # Number of days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
}

resource "google_storage_bucket" "aster_data_platform_landing" {
  project       = var.project_id
  name          = "${var.env}-aster-data-platform-landing"
  location      = var.region
  force_destroy = false

  uniform_bucket_level_access = true

  # Example Lifecycle Rule: Move data to Archive after 30 days
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }
}
```

---

**`error.tf`**

* Defines the critical Error Handling function and its trigger topic.
* `google_pubsub_topic "error_reprocess"`: Creates the Pub/Sub topic where other functions will send messages when they encounter errors.
* `google_cloudfunctions2_function "error_reprocess"`: Defines the Cloud Function itself.
    * `build_config`: Specifies the runtime (`python312`), entry point (`route` in `main.py`), and the source code location (the `zip_core` object uploaded in `main.tf`).
    * `service_config`: Configures runtime settings like memory (`256Mi`), timeout (`540s`), and crucial `environment_variables`:
        * `ENV`, `GCP_PROJECT`, `LOG_LEVEL`: Basic environment info.
        * `OPERATOR_IMPORT`: Tells `main.py` to load the `GoogleErrorReprocessOperator`.
        * `QUEUE_TOPIC_ERROR`: Itself, in case it needs to resubmit for retry after delay.
        * `QUEUE_TOPIC_EMAIL_SEND`, `QUEUE_TOPIC_SLACK_SEND`: Topics for sending notifications.
        * `QUEUE_TOPIC_PUBSUB_TO_BQ`: Topic for sending structured logs to BigQuery (via `var.queue_topic_pubsub_to_bq`).
        * `BIGQUERY_DATASET_ERROR`, `BIGQUERY_TABLE_ERROR`: Target for error logging.
        * `EMAIL_SENDER_ERROR`, `EMAIL_RECIPIENTS_ERROR`, `SLACK_CHANNELS_ERROR`: Notification details from `var.error_config`.
    * `event_trigger`: Configures the function to be triggered by messages published to the `google_pubsub_topic.error_reprocess.id` topic. `retry_policy = "RETRY_POLICY_RETRY"` means GCP will attempt redelivery on transient issues, but the operator logic handles application-level retries.
    * `depends_on`: Ensures the source code zip and necessary topics exist before creating the function.

```terraform
# modules/airless-core/error.tf

resource "google_pubsub_topic" "error_reprocess" {
  project = var.project_id
  name    = "${var.env}-error"
}

resource "google_cloudfunctions2_function" "error_reprocess" {
  project     = var.project_id
  name        = "${var.env}-error-reprocess"
  location    = var.region
  description = "Airless: Handles errors, retries, logging, and notifications."

  labels = {
    "airless-role" = "error-handler"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route" # Function name in main.py
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 100 # Adjust as needed
    min_instance_count  = 0   # Scale to zero when idle
    available_memory    = "256Mi"
    timeout_seconds     = 540 # Max timeout for Gen2 PubSub functions
    environment_variables = {
      ENV                      = var.env
      OPERATOR_IMPORT          = "from airless.google.cloud.core.operator import GoogleErrorReprocessOperator"
      GCP_PROJECT              = var.project_id
      LOG_LEVEL                = var.log_level
      # Self-reference for potential delayed retries
      QUEUE_TOPIC_ERROR        = google_pubsub_topic.error_reprocess.name
      # Notification topics (defined in email.tf/slack.tf)
      QUEUE_TOPIC_EMAIL_SEND   = google_pubsub_topic.error_notification_email_send.name
      QUEUE_TOPIC_SLACK_SEND   = google_pubsub_topic.error_notification_slack_send.name
      # Topic for structured logging (passed in as variable)
      QUEUE_TOPIC_PUBSUB_TO_BQ = var.queue_topic_pubsub_to_bq.name
      # Config from variables for the operator
      BIGQUERY_DATASET_ERROR   = var.error_config.bigquery.dataset
      BIGQUERY_TABLE_ERROR     = var.error_config.bigquery.table
      EMAIL_SENDER_ERROR       = var.error_config.email.sender
      EMAIL_RECIPIENTS_ERROR   = jsonencode(var.error_config.email.recipients) # Pass list as JSON string
      SLACK_CHANNELS_ERROR     = jsonencode(var.error_config.slack.channels)  # Pass list as JSON string
    }
    # Add service account email if using non-default permissions
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    trigger_region = var.region # Can be omitted to use function region
    event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic   = google_pubsub_topic.error_reprocess.id
    retry_policy   = "RETRY_POLICY_RETRY" # Basic GCP retry for infrastructure issues
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.error_reprocess,
    # Ensure notification topics exist before error function depends on them
    google_pubsub_topic.error_notification_email_send,
    google_pubsub_topic.error_notification_slack_send
    # var.queue_topic_pubsub_to_bq # Topic resource should be created outside the module
  ]
}
```

---

**`delay.tf`**

* Defines the Delay function and its topic.
* Structure is very similar to `error.tf`.
* `google_pubsub_topic "delay"`: Topic to send messages to when a delay is needed.
* `google_cloudfunctions2_function "delay"`:
    * `OPERATOR_IMPORT`: Set to load the `GoogleDelayOperator`.
    * `QUEUE_TOPIC_ERROR`: Specifies where this function should send errors if it fails.
    * `retry_policy = "RETRY_POLICY_DO_NOT_RETRY"`: This function's core job *is* delay/retry logic; standard GCP retries might interfere. Failures should likely go straight to the error topic.

```terraform
# modules/airless-core/delay.tf

resource "google_pubsub_topic" "delay" {
  project = var.project_id
  name    = "${var.env}-delay"
}

resource "google_cloudfunctions2_function" "delay" {
  project     = var.project_id
  name        = "${var.env}-delay"
  location    = var.region
  description = "Airless: Introduces delays into workflows (e.g., for retries, rate limiting)."

  labels = {
    "airless-role" = "delay-handler"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 100
    min_instance_count  = 0
    available_memory    = "256Mi"
    timeout_seconds     = 540
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.google.cloud.core.operator import GoogleDelayOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = var.log_level
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name # Send errors here
    }
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.delay.id
    # Usually, delay logic is precise; don't rely on GCP auto-retry here.
    # Errors should go to the main error handler via QUEUE_TOPIC_ERROR.
    retry_policy = "RETRY_POLICY_DO_NOT_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.delay,
    google_pubsub_topic.error_reprocess # Ensure error topic exists
  ]
}
```

---

**`redirect.tf`**

* Defines the Redirect function(s) and associated topics.
* Includes two topics/functions (`redirect` and `redirect_medium`) potentially for different scaling/resource needs (e.g., `redirect_medium` has more memory `512Mi`). This allows routing redirection tasks based on expected fan-out load.
* `google_cloudfunctions2_function "redirect"` / `"redirect_medium"`:
    * `OPERATOR_IMPORT`: Loads the `GoogleRedirectOperator`.
    * `QUEUE_TOPIC_ERROR`: Specifies the error topic.
    * `retry_policy = "RETRY_POLICY_RETRY"`: Basic GCP retries are acceptable here.

```terraform
# modules/airless-core/redirect.tf

resource "google_pubsub_topic" "redirect" {
  project = var.project_id
  name    = "${var.env}-redirect"
}

resource "google_pubsub_topic" "redirect_medium" {
  project = var.project_id
  name    = "${var.env}-redirect-medium" # Topic for potentially larger fan-outs
}


resource "google_cloudfunctions2_function" "redirect" {
  project     = var.project_id
  name        = "${var.env}-redirect"
  location    = var.region
  description = "Airless: Redirects/fans-out a single message to multiple topics."

  labels = {
    "airless-role" = "redirect-handler"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 10 # Lower default max instances, adjust if needed
    min_instance_count  = 0
    available_memory    = "256Mi"
    timeout_seconds     = 540
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.google.cloud.core.operator import GoogleRedirectOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = "DEBUG" # Often useful to debug redirection logic
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
    }
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.redirect.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.redirect,
    google_pubsub_topic.error_reprocess
  ]
}

resource "google_cloudfunctions2_function" "redirect_medium" {
  project     = var.project_id
  name        = "${var.env}-redirect-medium"
  location    = var.region
  description = "Airless: Redirects/fans-out (medium instance size)."

  labels = {
    "airless-role" = "redirect-handler-medium"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 10
    min_instance_count  = 0
    available_memory    = "512Mi" # More memory than standard redirect
    timeout_seconds     = 540
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.google.cloud.core.operator import GoogleRedirectOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = "DEBUG"
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
    }
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.redirect_medium.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.redirect_medium,
    google_pubsub_topic.error_reprocess
  ]
}
```

---

**`email.tf`**

* Defines functions and topics for sending emails.
* Separates topics/functions for regular notifications (`notification_email_send`) and error notifications (`error_notification_email_send`). This allows using different SMTP configurations (via Secret Manager secrets `smtp` vs `smtp_error`) or different scaling/retry policies if needed.
* `google_cloudfunctions2_function "notification_email_send"` / `"error_notification_email_send"`:
    * `OPERATOR_IMPORT`: Loads the `GoogleEmailSendOperator`.
    * `SECRET_SMTP`: Environment variable expected by the operator to specify the *name* of the secret in GCP Secret Manager containing SMTP credentials (e.g., host, port, user, password). The module assumes secrets named `smtp` and `smtp_error` exist.
    * `max_instance_count = 1`: Limits concurrency, often desirable for external notification systems to avoid rate limits or being flagged as spam.
    * `retry_policy = "RETRY_POLICY_RETRY"`: Allows GCP retries for transient SMTP issues.

```terraform
# modules/airless-core/email.tf

resource "google_pubsub_topic" "notification_email_send" {
  project = var.project_id
  name    = "${var.env}-notification-email-send"
}

# Separate topic/function for error emails allows different config/scaling if needed
resource "google_pubsub_topic" "error_notification_email_send" {
  project = var.project_id
  name    = "${var.env}-error-notification-email-send"
}

resource "google_cloudfunctions2_function" "notification_email_send" {
  project     = var.project_id
  name        = "${var.env}-notification-email-send"
  location    = var.region
  description = "Airless: Sends standard email notifications via configured SMTP secret ('smtp')."

  labels = {
    "airless-role" = "email-notifier"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 1 # Limit concurrency for email sending
    min_instance_count  = 0
    available_memory    = "256Mi"
    timeout_seconds     = 60 # Email sending should be quick
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.email.operator import GoogleEmailSendOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = var.log_level
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
      # Operator expects secret name containing SMTP details (host, port, user, pass)
      SECRET_SMTP       = "smtp"
    }
    # Requires permissions to access Secret Manager
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.notification_email_send.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.notification_email_send,
    google_pubsub_topic.error_reprocess
  ]
}

resource "google_cloudfunctions2_function" "error_notification_email_send" {
  project     = var.project_id
  name        = "${var.env}-error-notification-email-send"
  location    = var.region
  description = "Airless: Sends error email notifications via configured SMTP secret ('smtp_error')."

  labels = {
    "airless-role" = "email-error-notifier"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 1 # Limit concurrency
    min_instance_count  = 0
    available_memory    = "256Mi"
    timeout_seconds     = 540 # Allow longer timeout for potential error handling delays
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.email.operator import GoogleEmailSendOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = var.log_level
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
      # Use a potentially different secret for error emails
      SECRET_SMTP       = "smtp_error"
    }
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.error_notification_email_send.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.error_notification_email_send,
    google_pubsub_topic.error_reprocess
  ]
}
```

---

**`slack.tf`**

* Defines functions and topics for Slack notifications.
* Includes separate topics/functions for standard (`notification_slack_send`) and error (`error_notification_slack_send`) messages, allowing different Slack App configurations/tokens (via secrets like `slack_alert`) if needed.
* Adds a `slack_react` function/topic, presumably to add emoji reactions to messages, perhaps indicating processing status.
* `google_cloudfunctions2_function "notification_slack_send"` / `"error_notification_slack_send"` / `"slack_react"`:
    * `OPERATOR_IMPORT`: Loads `GoogleSlackSendOperator` or `GoogleSlackReactOperator`.
    * Environment variables point to the error topic. The operator likely expects Slack API tokens/details to be stored in Secret Manager (though the specific secret name isn't defined via env var here, the operator might have a default like `slack_alert` or `slack_token`).
    * `max_instance_count = 1` and short timeouts are common for notification functions.

```terraform
# modules/airless-core/slack.tf

resource "google_pubsub_topic" "notification_slack_send" {
  project = var.project_id
  name    = "${var.env}-notification-slack-message-send"
}

resource "google_pubsub_topic" "error_notification_slack_send" {
  project = var.project_id
  name    = "${var.env}-error-notification-slack-message-send"
}

resource "google_pubsub_topic" "slack_react" {
  project = var.project_id
  name    = "${var.env}-slack-react"
}

resource "google_cloudfunctions2_function" "notification_slack_send" {
  project     = var.project_id
  name        = "${var.env}-notification-slack-send"
  location    = var.region
  description = "Airless: Sends standard Slack notifications via configured API secret."

  labels = {
    "airless-role" = "slack-notifier"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 1 # Limit concurrency for Slack API calls
    min_instance_count  = 0
    available_memory    = "256Mi"
    timeout_seconds     = 540 # Generous timeout, but should be quick
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.slack.operator import GoogleSlackSendOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = var.log_level
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
      # Operator likely expects a Secret Manager secret name via convention or another env var
      # e.g., SLACK_SECRET_NAME = "slack_alert"
    }
    # service_account_email = google_service_account.airless_core.email # Needs Secret Manager access
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.notification_slack_send.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.notification_slack_send,
    google_pubsub_topic.error_reprocess
  ]
}


resource "google_cloudfunctions2_function" "error_notification_slack_send" {
  project     = var.project_id
  name        = "${var.env}-error-notification-slack-send"
  location    = var.region
  description = "Airless: Sends error Slack notifications via configured API secret."

  labels = {
    "airless-role" = "slack-error-notifier"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 1
    min_instance_count  = 0
    available_memory    = "256Mi"
    timeout_seconds     = 540
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.slack.operator import GoogleSlackSendOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = var.log_level
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
      # Operator likely expects a Secret Manager secret name
    }
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.error_notification_slack_send.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.error_notification_slack_send,
    google_pubsub_topic.error_reprocess
  ]
}

resource "google_cloudfunctions2_function" "slack_react" {
  project     = var.project_id
  name        = "${var.env}-slack-react"
  location    = var.region
  description = "Airless: Reacts to Slack messages (e.g., adds emojis)."

  labels = {
    "airless-role" = "slack-reactor"
    "environment"  = var.env
  }

  build_config {
    runtime     = "python312"
    entry_point = "route"
    source {
      storage_source {
        bucket = var.function_bucket.name
        object = google_storage_bucket_object.zip_core.name
      }
    }
  }

  service_config {
    max_instance_count  = 1
    min_instance_count  = 0
    available_memory    = "128Mi" # Reactions likely need less memory
    timeout_seconds     = 60      # Should be very quick
    environment_variables = {
      ENV               = var.env
      OPERATOR_IMPORT   = "from airless.slack.operator import GoogleSlackReactOperator"
      GCP_PROJECT       = var.project_id
      LOG_LEVEL         = var.log_level
      QUEUE_TOPIC_ERROR = google_pubsub_topic.error_reprocess.name
      # Operator likely expects a Secret Manager secret name
    }
    # service_account_email = google_service_account.airless_core.email
  }

  event_trigger {
    event_type   = "google.cloud.pubsub.topic.v1.messagePublished"
    pubsub_topic = google_pubsub_topic.slack_react.id
    retry_policy = "RETRY_POLICY_RETRY"
  }

  depends_on = [
    google_storage_bucket_object.zip_core,
    google_pubsub_topic.slack_react,
    google_pubsub_topic.error_reprocess
  ]
}
```

---

**`output.tf`**

* Defines the outputs of the module. These expose the names and IDs of the created resources, making them easily accessible for use in other parts of your Terraform configuration or for external reference.
* Outputs include bucket names and Pub/Sub topic details (both `id` and `name`).

```terraform
# modules/airless-core/output.tf

output "bucket_datalake_landing_tmp_name" {
  description = "Name of the temporary landing bucket."
  value       = google_storage_bucket.aster_data_platform_landing_tmp.name
}

output "bucket_datalake_raw_name" {
  description = "Name of the raw data bucket."
  value       = google_storage_bucket.aster_data_platform_raw.name
}

output "bucket_datalake_landing_name" {
  description = "Name of the main landing bucket."
  value       = google_storage_bucket.aster_data_platform_landing.name
}

# Outputting PubSub Topics (ID is often needed for triggers/permissions, name for reference/env vars)
output "queue_error" {
  description = "Error reprocess queue details."
  value = {
    id   = google_pubsub_topic.error_reprocess.id
    name = google_pubsub_topic.error_reprocess.name
  }
}

output "queue_delay" {
  description = "Delay queue details."
  value = {
    id   = google_pubsub_topic.delay.id
    name = google_pubsub_topic.delay.name
  }
}

output "queue_redirect" {
  description = "Redirect queue details."
  value = {
    id   = google_pubsub_topic.redirect.id
    name = google_pubsub_topic.redirect.name
  }
}

output "queue_redirect_medium" {
  description = "Redirect medium queue details."
  value = {
    id   = google_pubsub_topic.redirect_medium.id
    name = google_pubsub_topic.redirect_medium.name
  }
}

output "queue_notification_email_send" {
  description = "Standard notification email send queue details."
  value = {
    id   = google_pubsub_topic.notification_email_send.id
    name = google_pubsub_topic.notification_email_send.name
  }
}

output "queue_error_notification_email_send" {
  description = "Error notification email send queue details."
  value = {
    id   = google_pubsub_topic.error_notification_email_send.id
    name = google_pubsub_topic.error_notification_email_send.name
  }
}

output "queue_notification_slack_send" {
  description = "Standard notification Slack send queue details."
  value = {
    id   = google_pubsub_topic.notification_slack_send.id
    name = google_pubsub_topic.notification_slack_send.name
  }
}

output "queue_error_notification_slack_send" {
  description = "Error notification Slack send queue details."
  value = {
    id   = google_pubsub_topic.error_notification_slack_send.id
    name = google_pubsub_topic.error_notification_slack_send.name
  }
}

output "queue_slack_react" {
  description = "Slack react queue details."
  value = {
    id   = google_pubsub_topic.slack_react.id
    name = google_pubsub_topic.slack_react.name
  }
}

# Add other outputs as needed, e.g., service account emails if created within the module
```

This comprehensive setup provides the foundational, reusable Airless core infrastructure on GCP, managed effectively with Terraform. Remember to create the necessary secrets (`smtp`, `smtp_error`, Slack tokens) in GCP Secret Manager and grant appropriate IAM permissions to the Cloud Functions' service accounts (especially for accessing Pub/Sub, Storage, Secret Manager, and potentially BigQuery).