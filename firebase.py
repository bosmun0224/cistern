# firebase.py - Post sensor readings to Firebase Firestore REST API
import urequests
import time
import log

try:
    from config import FIREBASE_PROJECT_ID, FIREBASE_API_KEY
except ImportError:
    FIREBASE_PROJECT_ID = None
    FIREBASE_API_KEY = None

FIRESTORE_URL = "https://firestore.googleapis.com/v1/projects/{}/databases/(default)/documents"

# Socket timeout (seconds) for every Firestore request. urequests has no
# default timeout, so a half-open connection (stale NAT entry after an AP
# reboot) blocks the socket read forever and hangs the whole device — the
# main loop never runs again, so the software watchdog can never fire.
#
# Kept below main.WDT_TIMEOUT_MS (8s) on purpose: a stalled post should raise
# here and get buffered for retry, leaving the hardware watchdog as the
# backstop for blocking that a socket timeout cannot cover. Healthy posts
# complete in ~2s end to end.
REQUEST_TIMEOUT = 5

# Cleared permanently the first time urequests rejects the timeout kwarg, so
# older builds that lack the parameter cost one TypeError rather than one per
# request.
_timeout_supported = True


def _get_url(collection):
    """Build Firestore REST URL for a collection"""
    return FIRESTORE_URL.format(FIREBASE_PROJECT_ID) + "/" + collection


def _post(url, body):
    """POST with a socket timeout.

    If urequests predates the `timeout` kwarg it raises TypeError while binding
    arguments — before any network I/O — so falling back is safe here.
    """
    global _timeout_supported
    headers = {"Content-Type": "application/json"}
    if _timeout_supported:
        try:
            return urequests.post(url, data=body, headers=headers,
                                  timeout=REQUEST_TIMEOUT)
        except TypeError:
            _timeout_supported = False
            log.warn('urequests has no timeout support — posts can block')
    return urequests.post(url, data=body, headers=headers)


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
        "timestamp": {"timestampValue": data.get('_timestamp') or _iso_timestamp()},
        "expireAt": {"timestampValue": data.get('_expireAt') or _iso_timestamp_offset(30)},
    }

    # Optional device telemetry
    for key in ('rssi', 'free_mem', 'alloc_mem', 'uptime_s', 'reset_cause', 
                'wifi_reconnects', 'loop_time_ms', 'used_storage', 
                'total_storage', 'cpu_temp', 'vsys_v'):
        if key in data:
            if isinstance(data[key], float):
                fields[key] = {"doubleValue": data[key]}
            else:
                fields[key] = {"integerValue": str(data[key])}

    if 'version' in data:
        fields['version'] = {"stringValue": data['version']}

    if 'last_error' in data:
        fields['last_error'] = {"stringValue": data['last_error']}

    doc = {"fields": fields}

    try:
        import ujson
        body = ujson.dumps(doc)
    except ImportError:
        import json
        body = json.dumps(doc)

    r = None
    try:
        r = _post(url, body)
        if r.status_code in (200, 201):
            log.info(f'Firebase OK: {data["voltage"]}V')
            return True
        else:
            log.warn(f'Firebase HTTP {r.status_code}')
    except Exception as e:
        log.error(f'Firebase post failed: {e}')
    finally:
        if r:
            try:
                r.close()
            except:
                pass

    return False


def post_crash_log(traceback_text):
    """Post a crash log to Firestore."""
    if not FIREBASE_PROJECT_ID:
        return False
        
    url = _get_url("crash_reports") + "?key=" + FIREBASE_API_KEY
    
    fields = {
        "timestamp": {"timestampValue": _iso_timestamp()},
        "traceback": {"stringValue": traceback_text},
    }
    
    doc = {"fields": fields}
    
    try:
        import ujson
        body = ujson.dumps(doc)
    except ImportError:
        import json
        body = json.dumps(doc)

    r = None
    try:
        r = _post(url, body)
        if r.status_code in (200, 201):
            log.info('Firebase OK: Crash log uploaded')
            return True
        else:
            log.warn(f'Firebase HTTP {r.status_code} on crash log upload')
    except Exception as e:
        log.error(f'Firebase crash log upload failed: {e}')
    finally:
        if r:
            try:
                r.close()
            except:
                pass
                
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
