resource "google_storage_bucket" "function_bucket" {
    name     = "${var.env}-airless"
    location = var.region
}