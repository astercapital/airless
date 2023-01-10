
resource "google_pubsub_topic" "notification_email_send" {
  name = "${var.env}-notification-email-send"
}

resource "google_pubsub_topic" "notification_slack_send" {
  name = "${var.env}-notification-slack-send"
}

resource "google_pubsub_topic" "gcs_query_to_bigquery" {
  name = "${var.env}-gcs-query-to-bigquery"
}

resource "google_pubsub_topic" "error_reprocess" {
  name = "${var.env}-error-reprocess"
}

resource "google_pubsub_topic" "redirect" {
  name = "${var.env}-redirect"
}

resource "google_pubsub_topic" "pubsub_to_bq" {
  name = "${var.env}-pubsub-to-bq"
}

resource "google_pubsub_topic" "file_to_bq" {
  name = "${var.env}-file-to-bq"
}

resource "google_pubsub_topic" "file_batch_write_detect" {
  name = "${var.env}-file-batch-write-detect"
}

resource "google_pubsub_topic" "file_batch_write_process" {
  name = "${var.env}-file-batch-write-process"
}

resource "google_pubsub_topic" "gcs_move" {
  name = "${var.env}-gcs-move"
}

resource "google_pubsub_topic" "gcs_delete" {
  name = "${var.env}-gcs-delete"
}

resource "google_pubsub_topic" "delay" {
  name = "${var.env}-delay"
}