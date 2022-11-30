resource "google_storage_bucket" "function_bucket" {
    name     = "${var.env}-airless"
    location = var.region
}

resource "google_storage_bucket" "file_entrance" {
    name     = "${var.env}-file-entrance"
    location = var.region
}

resource "google_storage_bucket" "file_entrance_config" {
    name     = "${var.env}-file-entrance-config"
    location = var.region
}
