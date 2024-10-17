# Generate pubsub topic name
resource "google_pubsub_topic" "paste_bin" {
  name = "${var.env}-paste-bin"
}

# Generates an archive of the source code compressed as a .zip file.
data "archive_file" "source_paste_bin" {
    type        = "zip"
    source_dir  = "../"
    output_path = "/tmp/paste-bin.zip"
    excludes    = ["Pipfile", "Pipfile.lock", "README.md", "terraform"]
}

# Add source code zip to the Cloud Function's bucket
resource "google_storage_bucket_object" "zip_paste_bin" {
    source       = data.archive_file.source.output_path
    content_type = "application/zip"

    # Append to the MD5 checksum of the files's content
    # to force the zip to be updated as soon as a change occurs
    name         = "src-${data.archive_file.source.output_md5}.zip"
    bucket       = var.function_bucket_name

    # Dependencies are automatically inferred so these lines can be deleted
    depends_on   = [
        google_storage_bucket.function_bucket,  # declared in `storage.tf`
        data.archive_file.source_paste_bin
    ]
}

resource "google_cloudfunctions2_function" "paste_bin" {
    name                  = "${var.env}-paste_bin"
    location              = var.region 
    description           = "Cloud functions that get data from paste bin"

    build_config {
        runtime           = "python39"  # of course changeable
        entry_point       = "route"
        source {
            storage_source {
                bucket = var.function_bucket_name
                object = google_storage_bucket_object.zip_paste_bin.name    
            }
        }
    }

    service_config {
        max_instance_count    = 100
        available_memory      = "128Mi"
        timeout_seconds       = 540
        environment_variables = {
            ENV                     = var.env
            OPERATOR_IMPORT         = "from airless.operator.event import PasteBinOperator"
            GCP_REGION              = var.region
            GCP_PROJECT             = var.project_id
            LOG_LEVEL               = var.log_level

            PUBSUB_TOPIC_ERROR      = var.pubsub_topic_error_name

            GCS_BUCKET_LANDING_ZONE = var.raw_zone_bucket_name
        }
    }

    event_trigger {
        trigger_region = var.region
        event_type     = "google.cloud.pubsub.topic.v1.messagePublished"
        pubsub_topic   = google_pubsub_topic.delay.id
        retry_policy   = "RETRY_POLICY_DO_NOT_RETRY"
    }

    depends_on         = [
        google_storage_bucket_object.zip,
        google_pubsub_topic.paste_bin
    ]
}