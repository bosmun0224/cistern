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
    data: dict with voltage, depth_m, depth_pct, raw
    """
    if not FIREBASE_PROJECT_ID:
        print("Firebase not configured")
        return False

    url = _get_url("readings") + "?key=" + FIREBASE_API_KEY

    # Firestore REST API document format
    doc = {
        "fields": {
            "voltage": {"doubleValue": data['voltage']},
            "depth_m": {"doubleValue": data['depth_m']},
            "depth_pct": {"doubleValue": data['depth_pct']},
            "raw": {"integerValue": str(data['raw'])},
            "timestamp": {"timestampValue": _iso_timestamp()}
        }
    }

    try:
        import ujson
        body = ujson.dumps(doc)
    except ImportError:
        import json
        body = json.dumps(doc)

    try:
        r = urequests.post(url, data=body, headers={"Content-Type": "application/json"})
        if r.status_code in (200, 201):
            print(f"  Posted to Firebase: {data['depth_pct']}%")
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
