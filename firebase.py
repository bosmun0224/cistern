# firebase.py - Post sensor readings to Firebase Firestore REST API
import urequests
import time

try:
    from config import FIREBASE_PROJECT_ID, FIREBASE_API_KEY
except ImportError:
    FIREBASE_PROJECT_ID = None
    FIREBASE_API_KEY = None

FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/{}/databases/(default)/documents"


def _get_url(collection):
    """Build Firestore REST URL for a collection"""
    return FIRESTORE_URL.format(FIREBASE_PROJECT_ID) + "/" + collection


def post_reading(data):
    """
    Post a sensor reading to Firestore.
    data: dict with voltage, raw, and device telemetry fields
    """
    if not FIREBASE_PROJECT_ID:
        print("Firebase not configured")
        return False

    url = _get_url("readings") + "?key=" + FIREBASE_API_KEY

    # Firestore REST API document format
    fields = {
        "voltage": {"doubleValue": data['voltage']},
        "raw": {"integerValue": str(data['raw'])},
        "timestamp": {"timestampValue": _iso_timestamp()},
        "expireAt": {"timestampValue": _iso_timestamp_offset(30)},
    }

    # Optional device telemetry
    for key in ('rssi', 'free_mem', 'used_storage', 'total_storage', 'cpu_temp'):
        if key in data:
            if isinstance(data[key], float):
                fields[key] = {"doubleValue": data[key]}
            else:
                fields[key] = {"integerValue": str(data[key])}

    if 'version' in data:
        fields['version'] = {"stringValue": data['version']}

    doc = {"fields": fields}

    try:
        import ujson
        body = ujson.dumps(doc)
    except ImportError:
        import json
        body = json.dumps(doc)

    try:
        r = urequests.post(url, data=body, headers={"Content-Type": "application/json"})
        if r.status_code in (200, 201):
            print(f"  Posted to Firebase: {data['voltage']}V")
            r.close()
            return True
        else:
            print(f"  Firebase error: {r.status_code}")
            r.close()
    except Exception as e:
        print(f"  Firebase post failed: {e}")

    return False


def _iso_timestamp():
    """Generate ISO 8601 timestamp from RTC"""
    t = time.localtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def _iso_timestamp_offset(days):
    """Generate ISO 8601 timestamp `days` in the future."""
    t = time.localtime(time.time() + days * 86400)
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}Z".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )
