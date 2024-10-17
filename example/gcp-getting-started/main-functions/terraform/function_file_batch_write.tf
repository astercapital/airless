
resource "google_cloudfunctions2_function" "file_batch_write_detect" {
    name                  = "${var.env}-file-batch-write-detect"
    location              = var.region 
    description           = "Cloud Function to identify which files from a bucket are able to be processed considering some given thresholds"

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
        available_memory      = "512Mi"
        timeout_seconds       = 540
        environment_variables = {
            ENV                              = var.env
            OPERATOR_IMPORT                  = "from airless.operator.google.storage import BatchWriteDetectOperator"
            GCP_PROJECT                      = var.project_id
            PUBSUB_TOPIC_ERROR               = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                        = var.log_level
            PUBSUB_TOPIC_BATCH_WRITE_PROCESS = google_pubsub_topic.file_batch_write_process.name
            GCS_BUCKET_LANDING_ZONE          = google_storage_bucket.landing_zone.name
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.file_batch_write_detect.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.file_batch_write_detect,
        google_pubsub_topic.file_batch_write_process,
        google_storage_bucket.landing_zone_loader,
        google_storage_bucket.landing_zone
    ]
}

resource "google_cloudfunctions2_function" "file_batch_write_process" {
    name                  = "${var.env}-file-batch-write-process"
    location              = var.region 
    description           = "Cloud Function that merges files from a GCS bucket into one and sends them to the Data Lake Landing Zone Loader Bucket"

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
        max_instance_count    = 100
        available_memory      = "1Gi"
        timeout_seconds       = 540
        environment_variables = {
            ENV                               = var.env
            OPERATOR_IMPORT                   = "from airless.operator.google.storage import BatchWriteProcessOperator"
            GCP_PROJECT                       = var.project_id
            PUBSUB_TOPIC_ERROR                = google_pubsub_topic.error_reprocess.name
            LOG_LEVEL                         = var.log_level
            GCS_BUCKET_LANDING_ZONE           = google_storage_bucket.landing_zone.name
            GCS_BUCKET_LANDING_ZONE_PROCESSED = google_storage_bucket.landing_zone_processed.name
            GCS_BUCKET_LANDING_ZONE_LOADER    = google_storage_bucket.landing_zone_loader.name
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.file_batch_write_process.id
        retry_policy   = "RETRY_POLICY_RETRY"
    }

    depends_on         = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        google_storage_bucket_object.zip,
        google_pubsub_topic.file_batch_write_process,
        google_storage_bucket.landing_zone,
        google_storage_bucket.landing_zone_processed,
        google_storage_bucket.landing_zone_loader
    ]
}


resource "google_cloud_scheduler_job" "file_batch_write" {
  name        = "${var.env}-file-batch-write"
  description = "Scheduler to run file batch detect and identify which files can be processed from the Data Lake Landing Zone and load them to BQ"
  schedule    = "10,40 * * * *"
  time_zone   = "America/Sao_Paulo"

  pubsub_target {
    # topic.id is the topic's full resource name.
    topic_name = google_pubsub_topic.file_batch_write_detect.id
    data       = base64encode("{\"threshold\":{\"minutes\":30,\"size\":200000000,\"file_quantity\":100},\"metadata\":{\"max_retries\":0}}")
  }
}
