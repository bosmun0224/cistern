#!/usr/bin/env python3
"""Seed Firestore with realistic cistern readings for dashboard testing.

Writes 288 documents (24 hours × 12 per hour = 5-minute intervals) to the
'readings' collection.  The most recent reading lands at roughly "now" so
the dashboard shows the device as Online.

Usage:
    python3 -m tests.seed_firestore
"""

import json
import math
import os
import random
import urllib.request
from datetime import datetime, timezone, timedelta

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "cistern-blomquist")
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY", "AIzaSyCMvUgbaUvekblMsrPx7Pg9sPrmgB4iPk4")

FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
)

# Sensor / tank constants (mirrored from dashboard for realistic voltages)
V_MIN = 0.66
V_MAX = 3.3
DEPTH_MAX_M = 5.0
TANK_RADIUS_IN = 28.8
TANK_DIAMETER_IN = TANK_RADIUS_IN * 2
M_TO_IN = 39.3701

# The tank is only ~1.46m tall; max realistic depth in the sensor's 0-5m range
TANK_DEPTH_M = TANK_DIAMETER_IN / M_TO_IN  # ≈ 1.463m

NUM_READINGS = 288
INTERVAL_MIN = 5


def voltage_for_pct(pct):
    """Return a voltage corresponding to `pct`% of the actual tank height."""
    depth_m = (pct / 100) * TANK_DEPTH_M
    return V_MIN + (depth_m / DEPTH_MAX_M) * (V_MAX - V_MIN)


def raw_for_voltage(voltage):
    """Approximate raw ADC value for a given voltage."""
    return int(voltage * 32767 / 4.096)


def make_reading(ts, voltage):
    """Build a Firestore REST document from voltage + timestamp."""
    raw = raw_for_voltage(voltage)
    expire_at = ts + timedelta(days=30)
    fields = {
        "voltage": {"doubleValue": round(voltage, 4)},
        "raw": {"integerValue": str(raw)},
        "timestamp": {"timestampValue": ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
        "expireAt": {"timestampValue": expire_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")},
        # Simulated device telemetry
        "rssi": {"integerValue": str(random.randint(-70, -45))},
        "free_mem": {"integerValue": str(random.randint(80000, 120000))},
        "cpu_freq": {"integerValue": "125"},
        "total_storage": {"integerValue": "1048576"},
        "used_storage": {"integerValue": str(random.randint(200000, 400000))},
    }
    return {"fields": fields}


def post_doc(doc):
    url = f"{FIRESTORE_BASE}/readings?key={FIREBASE_API_KEY}"
    data = json.dumps(doc).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return resp.status


def main():
    now = datetime.now(timezone.utc)
    # Walk back from now so the last reading is ~now
    start = now - timedelta(minutes=INTERVAL_MIN * (NUM_READINGS - 1))

    # Simulate a gentle sine-wave fill level (40–80%)
    print(f"Seeding {NUM_READINGS} readings into Firestore …")
    ok = 0
    for i in range(NUM_READINGS):
        ts = start + timedelta(minutes=INTERVAL_MIN * i)
        pct = 60 + 20 * math.sin(2 * math.pi * i / NUM_READINGS)
        voltage = voltage_for_pct(pct) + random.uniform(-0.01, 0.01)
        doc = make_reading(ts, voltage)
        try:
            status = post_doc(doc)
            ok += 1
            if i % 50 == 0:
                print(f"  [{i+1}/{NUM_READINGS}] {ts.isoformat()} → {status}")
        except Exception as e:
            print(f"  [{i+1}/{NUM_READINGS}] FAILED: {e}")

    print(f"\nDone — {ok}/{NUM_READINGS} readings written.")


if __name__ == "__main__":
    main()
