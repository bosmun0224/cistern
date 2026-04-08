"""Integration tests that hit real endpoints (Firestore REST API, GitHub raw).

These tests require network access. Firestore tests verify the REST API
accepts valid readings and rejects malformed ones per the security rules.

Run:  python3 -m unittest tests.test_endpoints -v
"""

import json
import os
import unittest
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

# Config values (from config.py.example — these are public/non-secret)
FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "cistern-blomquist")
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyCMvUgbaUvekblMsrPx7Pg9sPrmgB4iPk4")
OTA_BASE_URL = os.environ.get(
    "OTA_BASE_URL",
    "https://raw.githubusercontent.com/bosmun0224/cistern/main/",
)

FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
)


def _firestore_reachable():
    """Quick check if Firestore API is accessible with the configured key."""
    url = f"{FIRESTORE_BASE}/readings?key={FIREBASE_API_KEY}&pageSize=1"
    try:
        urllib.request.urlopen(url)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False
        return True  # other errors mean the API is reachable
    except Exception:
        return False


@unittest.skipUnless(_firestore_reachable(), "Firestore API not accessible (check API key / security rules)")
class TestFirestoreEndpoint(unittest.TestCase):
    """Verify the Firestore REST API accepts valid readings and rejects bad ones."""

    def _post_reading(self, doc):
        url = f"{FIRESTORE_BASE}/readings?key={FIREBASE_API_KEY}"
        data = json.dumps(doc).encode()
        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return urllib.request.urlopen(req)

    def _delete_document(self, name):
        """Clean up a document by name (full resource path)."""
        url = f"https://firestore.googleapis.com/v1/{name}?key={FIREBASE_API_KEY}"
        req = urllib.request.Request(url, method="DELETE")
        try:
            urllib.request.urlopen(req)
        except urllib.error.HTTPError:
            pass  # security rules block delete — expected

    def _make_valid_doc(self):
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        expire = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        return {
            "fields": {
                "voltage": {"doubleValue": 1.98},
                "raw": {"integerValue": "15848"},
                "timestamp": {"timestampValue": ts},
                "expireAt": {"timestampValue": expire},
            }
        }

    def test_post_valid_reading(self):
        """A document with all required fields should be created (201)."""
        doc = self._make_valid_doc()
        resp = self._post_reading(doc)
        self.assertIn(resp.status, (200, 201))
        # attempt cleanup (may fail due to security rules)
        body = json.loads(resp.read())
        self._delete_document(body["name"])

    def test_post_missing_field_rejected(self):
        """A document missing 'raw' should be rejected by security rules."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        expire = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        doc = {
            "fields": {
                "voltage": {"doubleValue": 1.98},
                # raw is intentionally missing
                "timestamp": {"timestampValue": ts},
                "expireAt": {"timestampValue": expire},
            }
        }
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_reading(doc)
        self.assertEqual(ctx.exception.code, 403)

    def test_post_wrong_type_rejected(self):
        """A document with voltage as string should be rejected."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        expire = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        doc = {
            "fields": {
                "voltage": {"stringValue": "not_a_number"},
                "raw": {"integerValue": "15848"},
                "timestamp": {"timestampValue": ts},
                "expireAt": {"timestampValue": expire},
            }
        }
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self._post_reading(doc)
        self.assertEqual(ctx.exception.code, 403)

    def test_read_readings_collection(self):
        """Public read on the readings collection should succeed."""
        url = f"{FIRESTORE_BASE}/readings?key={FIREBASE_API_KEY}&pageSize=1"
        resp = urllib.request.urlopen(url)
        self.assertEqual(resp.status, 200)


class TestGitHubOTAEndpoint(unittest.TestCase):
    """Verify GitHub raw content is accessible for OTA updates."""

    def test_version_txt_reachable(self):
        """version.txt should be fetchable and contain a semver string."""
        url = OTA_BASE_URL + "version.txt"
        resp = urllib.request.urlopen(url)
        self.assertEqual(resp.status, 200)
        version = resp.read().decode().strip()
        parts = version.split(".")
        self.assertEqual(len(parts), 3, f"Expected semver, got: {version}")
        for part in parts:
            self.assertTrue(part.isdigit(), f"Non-numeric version component: {part}")

    def test_ota_files_reachable(self):
        """Each OTA-managed file should return 200 from GitHub raw."""
        ota_files = ["main.py", "sensor.py", "ota.py", "firebase.py", "provision.py"]
        for filename in ota_files:
            with self.subTest(file=filename):
                url = OTA_BASE_URL + filename
                resp = urllib.request.urlopen(url)
                self.assertEqual(resp.status, 200)
                content = resp.read().decode()
                self.assertGreater(len(content), 0, f"{filename} is empty")

    def test_nonexistent_file_returns_404(self):
        """A file that doesn't exist should 404, not silently succeed."""
        url = OTA_BASE_URL + "this_file_does_not_exist.py"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(url)
        self.assertEqual(ctx.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
