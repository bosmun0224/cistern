# Cistern Project

## Overview
Water level monitoring system using Raspberry Pi Pico W with OTA updates.

## Hardware
- **Pico W** (RP2040 + WiFi)
- **4-20mA depth sensor** (submersible pressure transducer)
- **HW-685** (4-20mA to voltage converter)
- **ADS1115** (16-bit I2C ADC)

## Wiring
```
4-20mA Sensor → HW-685 → ADS1115 (A0) → Pico W (I2C0: GP4/GP5)
```

## Files
- `boot.py` - WiFi connection or AP provisioning
- `main.py` - Main loop: read sensor, check OTA, post to Firebase
- `sensor.py` - ADS1115 + depth calculation
- `ota.py` - Over-the-air update logic
- `firebase.py` - Post readings to Firestore REST API
- `provision.py` - WiFi AP captive portal for setup
- `config.py` - WiFi creds, Firebase keys, OTA URL (gitignored)
- `dashboard/` - Static HTML dashboard for viewing data
- `infrastructure/` - Terraform for Firebase project setup

## Development
- Language: MicroPython
- Deploy: `mpremote cp *.py :`
- OTA: Push to GitHub, bump `version.txt`

## Calibration
- `V_MIN`: Voltage at 4mA (0 depth) ~0.66V
- `V_MAX`: Voltage at 20mA (max depth) ~3.3V
- `DEPTH_MAX`: Sensor max depth in meters
