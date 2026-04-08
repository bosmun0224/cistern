#!/usr/bin/env python3
"""Delete all documents from the Firestore 'readings' collection.

Uses gcloud OAuth token (security rules block API-key deletes).

Usage:
    python3 -m tests.cleanup_firestore
"""

import json
import os
import subprocess
import urllib.request
import urllib.error

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "cistern-blomquist")

FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
)


def get_access_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def list_documents(token, page_token=None):
    url = f"{FIRESTORE_BASE}/readings?pageSize=100"
    if page_token:
        url += f"&pageToken={page_token}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def delete_document(name, token):
    url = f"https://firestore.googleapis.com/v1/{name}"
    req = urllib.request.Request(url, method="DELETE", headers={"Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(req)
        return True
    except urllib.error.HTTPError:
        return False


def main():
    token = get_access_token()
    total = 0
    while True:
        data = list_documents(token)
        docs = data.get("documents", [])
        if not docs:
            break
        for doc in docs:
            name = doc["name"]
            if delete_document(name, token):
                total += 1
        next_page = data.get("nextPageToken")
        if not next_page:
            break
        data = list_documents(token, next_page)
    print(f"Deleted {total} documents.")


if __name__ == "__main__":
    main()
