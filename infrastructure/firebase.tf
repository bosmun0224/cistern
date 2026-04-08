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

resource "google_project_service" "identitytoolkit" {
  project            = google_project.cistern.project_id
  service            = "identitytoolkit.googleapis.com"
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
            match /config/{doc} {
              allow read: if true;
              allow write: if false;
            }
            match /readings/{reading} {
              allow read: if true;
              allow create: if request.resource.data.keys().hasAll(['voltage', 'raw', 'timestamp', 'expireAt'])
                           && request.resource.data.voltage is number
                           && request.resource.data.expireAt is timestamp;
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
  name         = "cloud.firestore"
  ruleset_name = google_firebaserules_ruleset.firestore.name

  depends_on = [google_firestore_database.default]
}

# --- Firestore TTL Policy (auto-delete docs after expireAt) ---
resource "google_firestore_field" "readings_ttl" {
  project    = google_project.cistern.project_id
  database   = google_firestore_database.default.name
  collection = "readings"
  field      = "expireAt"

  ttl_config {}

  # Keep default index behavior
  index_config {}

  depends_on = [google_firestore_database.default]
}

# --- Firebase Web App (required for API-key auth against Firestore) ---
resource "google_firebase_web_app" "dashboard" {
  provider     = google-beta
  project      = google_project.cistern.project_id
  display_name = "Cistern Dashboard"

  depends_on = [google_firebase_project.default]
}

# --- Firebase Auth (Identity Platform with anonymous sign-in) ---
resource "google_identity_platform_config" "auth" {
  project = google_project.cistern.project_id

  sign_in {
    anonymous {
      enabled = true
    }
  }

  depends_on = [google_project_service.identitytoolkit, google_firebase_project.default]
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
    api_targets {
      service = "datastore.googleapis.com"
    }
    api_targets {
      service = "identitytoolkit.googleapis.com"
    }
  }

  depends_on = [google_project_service.apikeys]
}

# --- Audit Logging (Firestore data access via datastore API) ---
resource "google_project_iam_audit_config" "firestore" {
  project = google_project.cistern.project_id
  service = "datastore.googleapis.com"

  audit_log_config {
    log_type = "ADMIN_READ"
  }
  audit_log_config {
    log_type = "DATA_READ"
  }
  audit_log_config {
    log_type = "DATA_WRITE"
  }
}
