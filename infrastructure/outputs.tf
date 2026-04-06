output "project_id" {
  value = var.project_id
}

output "firestore_database" {
  value = google_firestore_database.default.name
}
