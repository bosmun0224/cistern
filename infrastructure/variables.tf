variable "project_id" {
  description = "GCP/Firebase project ID"
  type        = string
}

variable "project_name" {
  description = "Display name for the project"
  type        = string
  default     = "Cistern Monitor"
}

variable "billing_account" {
  description = "GCP billing account ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}
