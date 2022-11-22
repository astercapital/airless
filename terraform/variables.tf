
variable "env" {
    default = "{dev|prod}"
}

variable "project_id" {
    default = "{project}"
}

variable "region" {
    default = "{region}"
}

variable "error" {
    type = object({
        bigquery = object({
            dataset = string
            table   = string
        })
        email = object({
            sender = string
            recipients = list(string)
        })
        slack = object({
            channels = list(string)
        })
    })
    default = {
        bigquery = {
            dataset = "errors"
            table = "persistent"
        }
        email = {
            sender = "Airless Alerts"
            recipients = ["{email}"]
        }
        slack = {
            channels = ["{channel}"]
        }
    }
}
