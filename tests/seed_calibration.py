#!/usr/bin/env python3
"""Seed the Firestore /config/calibration document.

This document stores sensor and tank calibration values that the
dashboard reads on load.  Edit the values below, then run once:

    python3 -m tests.seed_calibration

To update calibration later, re-run this script — it overwrites the
existing document via PATCH.
"""

import json
import os
import subprocess
import urllib.request

FIREBASE_PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "cistern-blomquist")

FIRESTORE_BASE = (
    f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
    f"/databases/(default)/documents"
)

# ---- Calibration values ----
# Adjust these to match your sensor + tank setup.
CALIBRATION = {
    # Sensor voltage range (220Ω shunt + 2:1 voltage divider, compensated)
    "v_min":          1.76,    # Voltage at ~8mA (sensor in air, 0 depth)
    "v_max":          4.40,    # Voltage at 20mA (sensor at max depth)
    "depth_max_m":    5.0,     # Sensor maximum depth rating in meters

    # Tank geometry (Norwesco 1500 gal horizontal cylinder)
    "tank_radius_in": 28.8,    # Tank cross-section radius in inches
    "tank_length_in": 133.0,   # Tank body length in inches
    "tank_max_gal":   1500,    # Rated capacity in gallons
}


def get_access_token():
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


def build_doc(cal):
    fields = {}
    for key, value in cal.items():
        if isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        else:
            fields[key] = {"doubleValue": value}
    return {"fields": fields}


def main():
    token = get_access_token()
    doc = build_doc(CALIBRATION)
    data = json.dumps(doc).encode()

    # PATCH to a named document (creates or overwrites)
    url = f"{FIRESTORE_BASE}/config/calibration"
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="PATCH",
    )

    resp = urllib.request.urlopen(req)
    if resp.status in (200, 201):
        print("Calibration document written to /config/calibration")
        for k, v in CALIBRATION.items():
            print(f"  {k}: {v}")
    else:
        print(f"Failed: HTTP {resp.status}")


if __name__ == "__main__":
    main()
