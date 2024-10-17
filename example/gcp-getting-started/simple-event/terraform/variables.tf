variable "project_id" {
  description = "Name of bucket raw"
  type        = string
}

variable "region" {
  description = "Region to create the function"
  type        = string
}

variable "env" {
  description = "Enviroment"
  type        = string
}

variable "log_level" {
  description = "Functions log level default"
  type        = string
}

variable "function_bucket_name" {
  description = "Name of the function bucket"
  type        = string
}

variable "raw_zone_bucket_name" {
  description = "GCS bucket where the raw zone from the data lake is located"
  type        = string
}

variable "pubsub_topic_error_name" {
  description = "Pubsub error topic name"
  type        = string
}
