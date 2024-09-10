
resource "google_cloudfunctions2_function" "gcs_move" {
    name                  = "${var.env}-gcs-move"
    location              = var.region 
    description           = "Cloud function that moves files inside GCS"

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
            ENV                                   = var.env
            OPERATOR_IMPORT                       = "from airless.operator.google.storage import FileMoveOperator"
            GCP_PROJECT                           = var.project_id
            PUBSUB_TOPIC_ERROR                    = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                             = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.gcs_move.id
        retry_policy   = "RETRY_POLICY_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.gcs_move
    ]
}

resource "google_cloudfunctions2_function" "gcs_delete" {
    name                  = "${var.env}-gcs-delete"
    location              = var.region 
    description           = "Cloud function that deletes files from GCS"

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
            ENV                                   = var.env
            OPERATOR_IMPORT                       = "from airless.operator.google.storage import FileDeleteOperator"
            GCP_PROJECT                           = var.project_id
            PUBSUB_TOPIC_ERROR                    = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                             = var.log_level
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.gcs_delete.id
        retry_policy   = "RETRY_POLICY_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.gcs_delete
    ]
}
