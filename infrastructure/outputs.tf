output "project_id" {
  value = google_project.cistern.project_id
}

output "firestore_database" {
  value = google_firestore_database.default.name
}

output "api_key" {
  value     = google_apikeys_key.cistern_key.key_string
  sensitive = true
}
