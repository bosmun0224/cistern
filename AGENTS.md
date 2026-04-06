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
- `boot.py` - WiFi connection on startup
- `main.py` - Main loop: read sensor, check OTA, report data
- `sensor.py` - ADS1115 + depth calculation
- `ota.py` - Over-the-air update logic
- `config.py` - WiFi creds & settings (gitignored)

## Development
- Language: MicroPython
- Deploy: `mpremote cp *.py :`
- OTA: Push to GitHub, bump `version.txt`

## Calibration
- `V_MIN`: Voltage at 4mA (0 depth) ~0.66V
- `V_MAX`: Voltage at 20mA (max depth) ~3.3V
- `DEPTH_MAX`: Sensor max depth in meters
