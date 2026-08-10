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
            // Optional-field helpers for Streamy. The web app clears a field by
            // writing an explicit null (an omitted field would leave the old
            // value in place on a masked update), so null has to pass.
            function optString(data, key, maxLen) {
              return !(key in data)
                  || data[key] == null
                  || (data[key] is string && data[key].size() <= maxLen);
            }
            function optInt(data, key, lo, hi) {
              return !(key in data)
                  || data[key] == null
                  || (data[key] is int && data[key] >= lo && data[key] <= hi);
            }
            function optNumber(data, key) {
              return !(key in data) || data[key] == null || data[key] is number;
            }

            match /config/{doc} {
              allow read: if true;
              allow write: if false;
            }
            match /readings/{reading} {
              allow read: if true;
              allow create: if request.resource.data.keys().hasAll(['voltage', 'raw', 'timestamp', 'expireAt'])
                           && request.resource.data.keys().hasOnly(['voltage', 'raw', 'timestamp', 'expireAt',
                                'rssi', 'free_mem', 'alloc_mem', 'uptime_s', 'reset_cause', 'wifi_reconnects', 'loop_time_ms', 'used_storage', 'total_storage', 'cpu_temp', 'version', 'last_error', 'vsys_v'])
                           && request.resource.data.voltage is number
                           && request.resource.data.raw is int
                           && request.resource.data.timestamp is timestamp
                           && request.resource.data.expireAt is timestamp;
              allow update, delete: if false;
            }
            match /crash_reports/{report} {
              allow read: if true;
              allow create: if request.resource.data.keys().hasAll(['timestamp', 'traceback'])
                           && request.resource.data.keys().hasOnly(['timestamp', 'traceback'])
                           && request.resource.data.timestamp is timestamp
                           && request.resource.data.traceback is string;
              allow update, delete: if false;
            }
            // --- Streamy (stream flow + trip log app) ---
            // Shared, unauthenticated read/write for a small group of friends.
            // The validation below is an abuse guard, not access control: it
            // caps document shape and size so a stray script can't fill the
            // database, but anyone who has the URL can write. Add Firebase Auth
            // here if that stops being an acceptable trade.
            match /streams/{siteId} {
              allow read: if true;
              allow create, update: if request.resource.data.keys().hasOnly(['site_id', 'name', 'state',
                                'usgs_name', 'lat', 'lng', 'ideal_min', 'ideal_max', 'notes', 'created_at'])
                           && request.resource.data.site_id is string
                           && request.resource.data.site_id.size() <= 20
                           && optString(request.resource.data, 'name', 120)
                           && optString(request.resource.data, 'state', 2)
                           && optString(request.resource.data, 'usgs_name', 200)
                           && optString(request.resource.data, 'notes', 4000)
                           && optNumber(request.resource.data, 'lat')
                           && optNumber(request.resource.data, 'lng')
                           && optNumber(request.resource.data, 'ideal_min')
                           && optNumber(request.resource.data, 'ideal_max');
              allow delete: if true;
            }
            match /trips/{trip} {
              allow read: if true;
              allow create, update: if request.resource.data.keys().hasAll(['site_id', 'date', 'rating'])
                           && request.resource.data.keys().hasOnly(['site_id', 'date', 'rating', 'clarity',
                                'clarity_note', 'flow_cfs', 'water_temp_f', 'anglers', 'fish', 'species',
                                'flies', 'notes', 'created_at'])
                           && request.resource.data.site_id is string
                           && request.resource.data.site_id.size() <= 20
                           && request.resource.data.date is string
                           && request.resource.data.date.size() == 10
                           && request.resource.data.rating is int
                           && request.resource.data.rating >= 1
                           && request.resource.data.rating <= 5
                           && optInt(request.resource.data, 'clarity', 1, 5)
                           && optInt(request.resource.data, 'fish', 0, 10000)
                           && optNumber(request.resource.data, 'flow_cfs')
                           && optNumber(request.resource.data, 'water_temp_f')
                           && optString(request.resource.data, 'clarity_note', 200)
                           && optString(request.resource.data, 'species', 200)
                           && optString(request.resource.data, 'flies', 300)
                           && optString(request.resource.data, 'anglers', 200)
                           && optString(request.resource.data, 'notes', 4000);
              allow delete: if true;
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
