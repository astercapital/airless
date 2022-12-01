
resource "google_cloudfunctions2_function" "file_detect" {
    name                  = "${var.env}-file-detect"
    location              = var.region 
    description           = "Cloud function that detects when a new file is uploaded to a bucket and triggers a cloud function to load the file to bigquery using some config information stored on a GCS bucket"

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
        max_instance_count    = 20
        available_memory      = "128Mi"
        timeout_seconds       = 60
        environment_variables = {
            ENV                             = var.env
            OPERATOR_IMPORT                 = "from airless.operator.google.storage import FileDetectOperator"
            GCP_PROJECT                     = var.project_id
            PUBSUB_TOPIC_ERROR              = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                       = var.log_level
            PUBSUB_TOPIC_FILE_TO_BQ         = google_pubsub_topic.file_detect.name
            GCS_BUCKET_FILE_ENTRANCE_CONFIG = google_storage_bucket.file_entrance_config.name
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.storage.object.v1.finalized"
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
        event_filters {
            attribute = "bucket"
            value = google_storage_bucket.file_entrance.name
        }
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.file_detect,
        google_storage_bucket.file_entrance,
        google_storage_bucket.file_entrance_config,
    ]
}

resource "google_cloudfunctions2_function" "file_to_bq" {
    name                  = "${var.env}-file-to-bq"
    location              = var.region 
    description           = "Cloud function that loads a file to bigquery. The file must be either a CSV or ndjson"

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
        max_instance_count    = 20
        available_memory      = "128Mi"
        timeout_seconds       = 540
        environment_variables = {
            ENV                     = var.env
            OPERATOR_IMPORT         = "from airless.operator.google.storage import FileToBigqueryOperator"
            GCP_PROJECT             = var.project_id
            PUBSUB_TOPIC_ERROR      = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL               = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.file_to_bq.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.file_to_bq
    ]
}
