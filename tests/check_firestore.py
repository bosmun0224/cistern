import json
import os
import subprocess
import urllib.request
import urllib.error

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "cistern-blomquist")

def get_access_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()

def get_last_readings(token, limit=20):
    url = f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}/databases/(default)/documents:runQuery"
    query = {
        "structuredQuery": {
            "from": [{"collectionId": "readings"}],
            "orderBy": [{"field": {"fieldPath": "timestamp"}, "direction": "DESCENDING"}],
            "limit": limit
        }
    }
    req = urllib.request.Request(url, method="POST", data=json.dumps(query).encode('utf-8'), headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def main():
    token = get_access_token()
    data = get_last_readings(token, 150)
    for doc in reversed(data):
        if "document" in doc:
            fields = doc["document"]["fields"]
            ts = fields.get("timestamp", {}).get("timestampValue", "N/A")
            volts = fields.get("voltage", {}).get("doubleValue", "N/A")
            if volts == "N/A":
                 volts = fields.get("voltage", {}).get("integerValue", "N/A")
            rssi = fields.get("rssi", {}).get("integerValue", "N/A")
            ver = fields.get("version", {}).get("stringValue", "N/A")
            temp = fields.get("cpu_temp", {}).get("doubleValue", "N/A")
            err = fields.get("last_error", {}).get("stringValue", "N/A")
            print(f"{ts} - {volts}V - RSSI {rssi} - v{ver} - Temp {temp} - Err: {err}")

if __name__ == "__main__":
    main()