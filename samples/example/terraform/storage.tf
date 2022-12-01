resource "google_storage_bucket" "function_bucket" {
    name     = "${var.env}-airless"
    location = var.region
}

resource "google_storage_bucket" "landing_zone" {
    name     = "${var.env}-landing-zone"
    location = var.region
}

resource "google_storage_bucket" "landing_zone_processed" {
    name          = "${var.env}-landing-zone-processed"
    location      = var.region
    storage_class = "COLDLINE"
}

resource "google_storage_bucket" "landing_zone_loader" {
    name     = "${var.env}-landing-zone-loader"
    location = var.region
}

resource "google_storage_bucket" "landing_zone_loader_config" {
    name     = "${var.env}-landing-zone-loader-config"
    location = var.region
}