# Cistern Water Level Monitor

Remote cistern water level monitoring using a Raspberry Pi Pico W with OTA updates.

## Hardware

| Component | Purpose |
|-----------|---------|
| Pico W | Microcontroller with WiFi |
| 4-20mA depth sensor | Submersible pressure transducer (5m range) |
| MT3608 | DC-DC boost converter (5V → 24V) |
| 220Ω resistor (×2) | Shunt + voltage divider (in series) |
| ADS1115 | 16-bit ADC (I2C) |

## Wiring

The 4-20mA sensor is powered by 24V from the MT3608 boost converter. Current flows through two 220Ω resistors in series (440Ω total). The ADS1115 reads the midpoint, which is half the total voltage — safe for the 3.3V ADC.

```
 MT3608 24V ──── Sensor RED (+)
                 Sensor BLACK (-) ──┬── 220Ω ──┬── 220Ω ──── GND
                                    │           │
                               (full shunt)  ADS1115 A0
                               (1.76-4.40V) (0.88-2.20V)
```

**Pin connections:**

| From | To |
|------|-----|
| Pico VBUS (5V) | MT3608 IN+ |
| Pico GND | MT3608 IN- |
| MT3608 OUT+ (24V) | Sensor Red (+) |
| Sensor Black (-) | 220Ω → midpoint → 220Ω → GND |
| Divider midpoint | ADS1115 A0 |
| Pico 3V3 | ADS1115 VDD |
| Pico GND | ADS1115 GND |
| ADS1115 GND | ADS1115 ADDR (address 0x48) |
| Pico GP4 | ADS1115 SDA |
| Pico GP5 | ADS1115 SCL |

## Calibration

| Parameter | Value | Notes |
|-----------|-------|-------|
| v_min | 1.76V | Sensor in air (~8mA), after ×2 divider compensation |
| v_max | 4.40V | Sensor at max depth (20mA), after ×2 divider compensation |
| depth_max_m | 5.0 | Sensor maximum depth rating |
| tank_radius_in | 28.8 | Norwesco 1500 gal horizontal cylinder |
| tank_length_in | 133 | Tank body length |

Software applies `DIVIDER_RATIO = 2.0` to the raw ADC voltage to recover the actual shunt voltage.

## Setup

### Flashing MicroPython (Fresh or Re-flash)

**Requirements:**

```bash
brew install picotool
pip install mpremote
```

**1. Enter BOOTSEL mode:** Hold the BOOTSEL button on the Pico W while plugging it into USB.

**2. Erase the entire flash** (removes all code and filesystem):

```bash
picotool erase --all
```

**3. Download and flash MicroPython:**

Download the latest Pico W firmware from [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/), then:

```bash
picotool load RPI_PICO_W-<version>.uf2
picotool reboot
```

**4. Verify the Pico W is running MicroPython:**

```bash
mpremote connect list
```

You should see a device like `/dev/cu.usbmodem*` listed as `MicroPython Board in FS mode`.

> **Important:** Always use `picotool` for flashing — do NOT drag-and-drop `.uf2` files to `/Volumes/RPI-RP2`. macOS may report the copy as successful before the data is fully written, resulting in a corrupted or incomplete flash. The `picotool erase --all` command is also necessary to wipe the MicroPython filesystem area where user scripts (`boot.py`, `main.py`, etc.) are stored — a firmware-only flash leaves old code intact.

### Upload Cistern Code

```bash
mpremote cp boot.py main.py sensor.py ota.py firebase.py provision.py config.py.example :
```

### Provision WiFi

1. Power on the Pico — it starts a **"Cistern-Setup"** WiFi hotspot
2. Connect your phone to it (password: `cistern123`)
3. Enter the home WiFi credentials in the setup page
4. Pico saves, reboots, and starts monitoring

## Firebase

Readings are posted to Firestore every 60 seconds.

### Infrastructure

```bash
cd infrastructure
cp terraform.tfvars.example terraform.tfvars  # set your project ID
./init.sh
terraform apply
```

### Dashboard

A single-page dashboard in `dashboard/index.html` — deploy anywhere (GitHub Pages, Vercel, etc.).

1. Edit `dashboard/index.html` and set `FIREBASE_PROJECT_ID` and `FIREBASE_API_KEY`
2. Open in a browser or deploy

Shows: water level gauge, depth, voltage, 24h history chart, device telemetry.
```

## OTA Updates

The Pico checks for updates on boot by comparing `version.txt` with the remote version.

To push an update:
1. Edit code in this repo
2. Bump `version.txt`
3. Push to GitHub
4. Pico downloads new files on next boot

## Troubleshooting via USB

Connect to the Pico W over USB for hardware debugging using `mpremote`:

```bash
mpremote connect /dev/cu.usbmodem* repl
```

### Entering the REPL

There are two ways to drop into the MicroPython REPL:

1. **Ctrl+C** — Press Ctrl+C during the 3-second boot delay, or at any time while the main loop is running.
2. **Debug jumper** — Connect GP15 to GND before powering on. This skips all code and drops straight to the REPL.

### Useful REPL Commands

```python
# Scan for I2C devices (ADS1115 should be at 0x48)
from sensor import scan_i2c
scan_i2c()

# Take a sensor reading
from sensor import read_sensor
read_sensor()

# Check WiFi status
import network
wlan = network.WLAN(network.STA_IF)
wlan.isconnected(), wlan.ifconfig()

# List files on the device
import os
os.listdir()

# Read the config
with open('config.py') as f: print(f.read())

# Reboot the device
import machine
machine.reset()
```

## Files

| File | Purpose |
|------|---------|
| `boot.py` | WiFi connection or provisioning on startup |
| `main.py` | Main loop: read sensor, post to Firebase |
| `sensor.py` | ADS1115 driver, returns raw voltage |
| `ota.py` | Over-the-air update logic |
| `firebase.py` | Post readings to Firestore |
| `provision.py` | WiFi AP provisioning (captive portal) |
| `config.py.example` | Config template (gitignored when copied) |
| `version.txt` | Current firmware version |
| `dashboard/` | Web dashboard (static HTML) |
| `infrastructure/` | Terraform for Firebase setup |

## Calibration

Calibration values are stored in Firestore at `/config/calibration` and loaded by the dashboard on page load. This means you can recalibrate without redeploying anything.

Edit `tests/seed_calibration.py` to match your sensor and tank, then run:

```bash
python3 -m tests.seed_calibration
```

| Field | Default | Description |
|-------|---------|-------------|
| `v_min` | 0.66 | Voltage at 4mA (sensor reads 0 depth) |
| `v_max` | 3.3 | Voltage at 20mA (sensor reads max depth) |
| `depth_max_m` | 5.0 | Sensor maximum depth rating in meters |
| `tank_radius_in` | 28.8 | Tank cross-section radius in inches |
| `tank_length_in` | 133.0 | Tank body length in inches |
| `tank_max_gal` | 1500 | Rated capacity in gallons |

If the config document doesn't exist, the dashboard falls back to the defaults above.

The Pico sends only raw voltage — all depth/volume computation happens client-side on the dashboard using the horizontal cylinder formula.

## License

MIT
