# --- GCP Project ---
resource "google_project" "cistern" {
  name            = var.project_name
  project_id      = var.project_id
  billing_account = var.billing_account
}

# --- Enable APIs ---
resource "google_project_service" "firebase" {
  project            = google_project.cistern.project_id
  service            = "firebase.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firestore" {
  project            = google_project.cistern.project_id
  service            = "firestore.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "apikeys" {
  project            = google_project.cistern.project_id
  service            = "apikeys.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "firebaserules" {
  project            = google_project.cistern.project_id
  service            = "firebaserules.googleapis.com"
  disable_on_destroy = false
}

# --- Firebase Project ---
resource "google_firebase_project" "default" {
  provider = google-beta
  project  = google_project.cistern.project_id

  depends_on = [google_project_service.firebase]
}

# --- Firestore Database ---
resource "google_firestore_database" "default" {
  project                 = google_project.cistern.project_id
  name                    = "(default)"
  location_id             = var.region
  type                    = "FIRESTORE_NATIVE"
  delete_protection_state = "DELETE_PROTECTION_ENABLED"
  deletion_policy         = "ABANDON"

  depends_on = [google_project_service.firestore]
}

# --- Firestore Security Rules ---
resource "google_firebaserules_ruleset" "firestore" {
  provider = google-beta
  project  = google_project.cistern.project_id

  source {
    files {
      name    = "firestore.rules"
      content = <<-EOT
        rules_version = '2';
        service cloud.firestore {
          match /databases/{database}/documents {
            match /readings/{reading} {
              allow read: if true;
              allow create: if request.resource.data.keys().hasAll(['voltage', 'depth_m', 'depth_pct', 'raw', 'timestamp'])
                           && request.resource.data.voltage is number
                           && request.resource.data.depth_m is number
                           && request.resource.data.depth_pct is number;
              allow update, delete: if false;
            }
            match /{document=**} {
              allow read, write: if false;
            }
          }
        }
      EOT
    }
  }

  depends_on = [google_firebase_project.default]
}

resource "google_firebaserules_release" "firestore" {
  provider     = google-beta
  project      = google_project.cistern.project_id
  name         = "cloud.firestore/database=default"
  ruleset_name = google_firebaserules_ruleset.firestore.name

  depends_on = [google_firestore_database.default]
}

# --- API Key (for Pico + Dashboard) ---
resource "google_apikeys_key" "cistern_key" {
  name         = "cistern-api-key"
  display_name = "Cistern API Key"
  project      = google_project.cistern.project_id

  restrictions {
    api_targets {
      service = "firestore.googleapis.com"
    }
  }

  depends_on = [google_project_service.apikeys]
}
