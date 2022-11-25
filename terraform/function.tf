# Generates an archive of the source code compressed as a .zip file.
data "archive_file" "source" {
    type        = "zip"
    source_dir  = "../"
    output_path = "/tmp/function.zip"
    excludes    = [
        "Pipfile", "Pipfile.lock", "samples",
        "dist", "airless.egg-info", "terraform",
        "tests", ".git", ".gitignore", ".gcloudignore",
        "LICENSE", "pyproject.toml", "README.md",
        "setup.cfg"
    ]
}

# Add source code zip to the Cloud Function's bucket
resource "google_storage_bucket_object" "zip" {
    source       = data.archive_file.source.output_path
    content_type = "application/zip"

    # Append to the MD5 checksum of the files's content
    # to force the zip to be updated as soon as a change occurs
    name         = "src-${data.archive_file.source.output_md5}.zip"
    bucket       = google_storage_bucket.function_bucket.name

    # Dependencies are automatically inferred so these lines can be deleted
    depends_on   = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        data.archive_file.source
    ]
}

resource "google_cloudfunctions2_function" "notification_email_send" {
    name                  = "${var.env}-notification-email-send"
    location              = var.region 
    description           = "Cloud function the receives the email subject, content, recipients, sender name and attachments and sends an email using the SMTP server configured using the Cloud Secret Manager with name `smtp`"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = google_storage_bucket.function_bucket.name
                object = google_storage_bucket_object.zip.name    
            }
        }
    }

    service_config {
        max_instance_count    = 1
        available_memory      = "256Mi"
        timeout_seconds       = 60
        environment_variables = {
            ENV                       = var.env
            OPERATOR_IMPORT           = "from airless.operator.notification.email import EmailSendOperator"
            GCP_PROJECT               = var.project_id
            PUBSUB_TOPIC_ERROR        = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                 = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.notification_email_send.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.notification_email_send
    ]
}

resource "google_cloudfunctions2_function" "notification_slack_send" {
    name                  = "${var.env}-notification-slack-send"
    location              = var.region 
    description           = "Cloud function the receives the the content and a list of channels and sends a slack message using Slack's API configured using the Cloud Secret Manager with name `slack_alert`"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = google_storage_bucket.function_bucket.name
                object = google_storage_bucket_object.zip.name    
            }
        }
    }

    service_config {
        max_instance_count    = 1
        available_memory      = "128Mi"
        timeout_seconds       = 60
        environment_variables = {
            ENV                     = var.env
            OPERATOR_IMPORT         = "from airless.operator.notification.slack import SlackSendOperator"
            GCP_PROJECT             = var.project_id
            PUBSUB_TOPIC_ERROR      = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL               = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.notification_slack_send.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.notification_slack_send
    ]
}

resource "google_cloudfunctions2_function" "error_reprocess" {
    name                  = "${var.env}-error-reprocess"
    location              = var.region 
    description           = "Cloud functions that manages errors from all other cloud functions including retry strategies, delay strategies, etc"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = google_storage_bucket.function_bucket.name
                object = google_storage_bucket_object.zip.name    
            }
        }
    }

    service_config {
        max_instance_count    = 1
        available_memory      = "256Mi"
        timeout_seconds       = 540
        environment_variables = {
            ENV                       = var.env
            OPERATOR_IMPORT           = "from airless.operator.error import ErrorReprocessOperator"
            GCP_PROJECT               = var.project_id
            PUBSUB_TOPIC_ERROR        = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                 = var.log_level
            PUBSUB_TOPIC_EMAIL_SEND   = google_pubsub_topic.notification_email_send.name
            PUBSUB_TOPIC_SLACK_SEND   = google_pubsub_topic.notification_slack_send.name
            BIGQUERY_DATASET_ERROR    = var.error.bigquery.dataset
            BIGQUERY_TABLE_ERROR      = var.error.bigquery.table
            EMAIL_SENDER_ERROR        = var.error.email.sender
            EMAIL_RECIPIENTS_ERROR    = jsonencode(var.error.email.recipients)
            SLACK_CHANNELS_ERROR      = jsonencode(var.error.slack.channels)
            PUBSUB_TOPIC_PUBSUB_TO_BQ = google_pubsub_topic.pubsub_to_bq.name
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.error_reprocess.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.error_reprocess
    ]
}

resource "google_cloudfunctions2_function" "gcs_query_to_bigquery" {
    name                  = "${var.env}-gcs-query-to-bigquery"
    location              = var.region 
    description           = "Cloud functions that reads a SQL file stored on a GCS bucket and runs it on BigQuery"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = google_storage_bucket.function_bucket.name
                object = google_storage_bucket_object.zip.name    
            }
        }
    }

    service_config {
        max_instance_count    = 1
        available_memory      = "128Mi"
        timeout_seconds       = 60
        environment_variables = {
            ENV                     = var.env
            OPERATOR_IMPORT         = "from airless.operator.google.bigquery import GcsQueryToBigqueryOperator"
            GCP_PROJECT             = var.project_id
            PUBSUB_TOPIC_ERROR      = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL               = var.log_level
            GCS_BUCKET_SQL          = "${var.project_id}-sql"
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.gcs_query_to_bigquery.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.gcs_query_to_bigquery
    ]
}

resource "google_cloudfunctions2_function" "redirect" {
    name                  = "${var.env}-redirect"
    location              = var.region 
    description           = "Cloud functions that receives one pubsub event and transforms it into multiple pubsub events"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = google_storage_bucket.function_bucket.name
                object = google_storage_bucket_object.zip.name    
            }
        }
    }

    service_config {
        max_instance_count    = 10
        available_memory      = "128Mi"
        timeout_seconds       = 540
        environment_variables = {
            ENV                     = var.env
            OPERATOR_IMPORT         = "from airless.operator.redirect import RedirectOperator"
            GCP_PROJECT             = var.project_id
            PUBSUB_TOPIC_ERROR      = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL               = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.redirect.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.redirect
    ]
}


resource "google_cloudfunctions2_function" "pubsub_to_bq" {
    name                  = "${var.env}-pubsub-to-bq"
    location              = var.region 
    description           = "Cloud functions that writes pubsub messages to Bigquery"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = google_storage_bucket.function_bucket.name
                object = google_storage_bucket_object.zip.name    
            }
        }
    }

    service_config {
        max_instance_count    = 50
        available_memory      = "256Mi"
        timeout_seconds       = 180
        environment_variables = {
            ENV                     = var.env
            OPERATOR_IMPORT         = "from airless.operator.google.bigquery import PubsubToBqOperator"
            GCP_PROJECT             = var.project_id
            PUBSUB_TOPIC_ERROR      = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL               = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.pubsub_to_bq.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.pubsub_to_bq
    ]
}