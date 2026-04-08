"""
Delete all documents from the Firestore readings collection.

Uses batch delete via the REST API with OAuth (gcloud auth).
Security rules block delete with API keys, so this uses
a gcloud access token instead.

Usage:
    python3 cistern/cleanup_firestore.py
"""

import json
import subprocess
import urllib.request
import urllib.error

PROJECT_ID = "cistern-blomquist"
API_KEY = "AIzaSyCMvUgbaUvekblMsrPx7Pg9sPrmgB4iPk4"
FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}"
    f"/databases/(default)/documents"
)
PAGE_SIZE = 100


def get_access_token():
    """Get OAuth token from gcloud CLI."""
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gcloud auth failed: {result.stderr}")
    return result.stdout.strip()


def list_documents(token, page_token=None):
    """List document names from the readings collection."""
    url = f"{FIRESTORE_BASE}/readings?pageSize={PAGE_SIZE}"
    if page_token:
        url += f"&pageToken={page_token}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    docs = [d["name"] for d in data.get("documents", [])]
    next_token = data.get("nextPageToken")
    return docs, next_token


def delete_document(token, name):
    """Delete a single document by its full resource name."""
    url = f"https://firestore.googleapis.com/v1/{name}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        print(f"  Failed to delete {name}: {e.code}")
        return e.code


def main():
    token = get_access_token()
    total_deleted = 0
    page_token = None

    print(f"Cleaning up readings from Firestore ({PROJECT_ID})...")

    while True:
        docs, page_token = list_documents(token, page_token)
        if not docs:
            break

        for name in docs:
            delete_document(token, name)
            total_deleted += 1

        print(f"  Deleted {total_deleted} documents so far...")

        if not page_token:
            break

    print(f"Done. Deleted {total_deleted} documents total.")


if __name__ == "__main__":
    main()
