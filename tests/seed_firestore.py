"""
Seed Firestore with bootstrap cistern readings.
Generates ~288 readings (24 hours at 5-minute intervals) with
realistic depth fluctuations.

Usage:
    python3 cistern/seed_firestore.py
"""

import json
import math
import random
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

PROJECT_ID = "cistern-blomquist"
API_KEY = "AIzaSyCMvUgbaUvekblMsrPx7Pg9sPrmgB4iPk4"
FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT_ID}"
    f"/databases/(default)/documents"
)

# Sensor calibration (matches sensor.py)
V_MIN = 0.66
V_MAX = 3.3
DEPTH_MAX = 5.0

# Tank geometry (matches sensor.py)
TANK_RADIUS = 28.8
TANK_LENGTH = 133.0
TANK_MAX_GAL = 1500
M_TO_IN = 39.3701

# Seed params
NUM_READINGS = 288  # 24h at 5-min intervals
INTERVAL_MIN = 5
BASE_DEPTH_PCT = 72.0  # starting depth %


def depth_to_voltage(depth_pct):
    """Convert depth percentage back to voltage."""
    return V_MIN + (depth_pct / 100.0) * (V_MAX - V_MIN)


def voltage_to_raw(voltage):
    """Approximate raw ADC value from voltage (ADS1115 at gain=1, 3.3V ref)."""
    return int((voltage / 4.096) * 32767)


def depth_to_gallons(depth_m):
    """Convert depth in meters to gallons for horizontal cylinder tank."""
    h = depth_m * M_TO_IN
    R = TANK_RADIUS
    if h <= 0:
        return 0.0
    if h >= 2 * R:
        return TANK_MAX_GAL
    area = R * R * math.acos((R - h) / R) - (R - h) * math.sqrt(2 * R * h - h * h)
    return (area * TANK_LENGTH) / 231.0


def make_reading(depth_pct, ts):
    """Build a Firestore REST document from depth % and timestamp."""
    depth_pct = max(0.0, min(100.0, depth_pct))
    depth_m = (depth_pct / 100.0) * DEPTH_MAX
    voltage = depth_to_voltage(depth_pct)
    raw = voltage_to_raw(voltage)
    gallons = depth_to_gallons(depth_m)

    return {
        "fields": {
            "voltage": {"doubleValue": round(voltage, 4)},
            "depth_m": {"doubleValue": round(depth_m, 3)},
            "depth_pct": {"doubleValue": round(depth_pct, 2)},
            "gallons": {"doubleValue": round(gallons, 1)},
            "raw": {"integerValue": str(raw)},
            "timestamp": {"timestampValue": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
        }
    }


def post_document(doc):
    """POST a single document to Firestore."""
    url = f"{FIRESTORE_BASE}/readings?key={API_KEY}"
    data = json.dumps(doc).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def generate_readings():
    """Generate realistic depth readings with slow drift and small noise.
    The last reading lands at now so the dashboard shows 'Online'.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(minutes=INTERVAL_MIN * (NUM_READINGS - 1))

    readings = []

    for i in range(NUM_READINGS):
        ts = start + timedelta(minutes=INTERVAL_MIN * i)

        # Slow sinusoidal drift (simulates usage / refill cycle)
        drift = 8.0 * math.sin(2 * math.pi * i / NUM_READINGS)
        # Small random noise
        noise = random.gauss(0, 0.3)

        depth_pct = BASE_DEPTH_PCT + drift + noise
        readings.append((depth_pct, ts))

    return readings


def main():
    readings = generate_readings()
    total = len(readings)
    print(f"Seeding {total} readings into Firestore ({PROJECT_ID})...")

    for idx, (depth_pct, ts) in enumerate(readings, 1):
        doc = make_reading(depth_pct, ts)
        status = post_document(doc)
        if idx % 50 == 0 or idx == total:
            print(f"  [{idx}/{total}] status={status}  depth={depth_pct:.1f}%  ts={ts.isoformat()}")

    print("Done.")


if __name__ == "__main__":
    main()
