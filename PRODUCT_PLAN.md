# Cistern Monitor — Product Plan

## Current State
- Pico W + ADS1115 breakout + 4-20mA pressure sensor (220Ω shunt)
- RS-15-5 (120VAC → 5VDC) power supply tapped off well pump wiring
- Single-device Firestore (`readings` collection, `config/calibration`)
- Dashboard at cistern.vercel.app (Chart.js, smoothing, auto-scale)
- MicroPython firmware with OTA updates via GitHub raw

## Target Product
Sellable cistern/tank monitoring kit with per-customer dashboards.

---

## Competitive Analysis — PTLevel (only real competitor)

PTLevel by Paremtech (Ontario, Canada) is the market leader for remote cistern/tank monitoring. Amazon's Choice, $300+, 216 reviews (4.1★). This is the product to beat.

### PTLevel Product Line

| Product | Price | Notes |
|---------|-------|-------|
| Long Range Wireless PTLevel | $300 USD | LoRa transmitter (battery) + WiFi receiver (plugged in indoors). Most popular. |
| Wired WiFi PTLevel | $210–396 USD | Direct WiFi, requires power at the tank. |
| Deep Well PTLevel | $500–525 USD | Extended-range transducer for deep wells. |
| Refurbished LRW PTLevel | $250 USD | Discounted returned units. |

### PTLevel Software Tiers

**Free tier (included with hardware):**
- 1 month of history
- 2 alert set points max
- 1 alert recipient only
- Percentage readout only — no gallons/litres
- No CSV/data export
- Delivery company sharing

**Premium — $5 CAD/mo ($3.65 USD) or $50 CAD/yr ($37 USD):**
- 2 years of history with zoom controls
- CSV download of history data
- Unlimited alert set points
- Multiple alert recipients
- Gallons/litres readout
- Public sharing URL

### PTLevel Weaknesses (from Amazon reviews + product research)
1. **Pressure tube waterlogging** — #1 complaint. Air tube between transmitter and pressure chamber fills with water over time, causing wildly inaccurate readings. Happens every 2–4 months for some users.
2. **90s-era web UI** — basic HTML dashboard, no interactive charts, no modern app experience. Account is at ptdevices.com, plain login form.
3. **Gallons locked behind paywall** — free tier only shows percentage. Customers pay $300 for hardware and can't even see how many gallons they have.
4. **Two-piece architecture** — LRW version requires an indoor WiFi receiver plugged into an outlet PLUS an outdoor battery transmitter. More hardware, more failure points.
5. **1 month of free history** — useless for seasonal usage analysis or spotting slow leaks.
6. **No push notifications** — alerts are email/SMS only, no native mobile push.
7. **No volume calculation** — doesn't model tank geometry. Just depth percentage.

### Our Advantages (software-first approach)

| Feature | PTLevel Free | PTLevel Premium | Us (included) |
|---------|-------------|----------------|---------------|
| Gallons/volume readout | ❌ | ✅ | ✅ |
| Tank geometry modeling | ❌ | ❌ | ✅ (rectangular, dome, cylinder) |
| Interactive zoomable charts | ❌ | ❌ | ✅ (Chart.js with zoom + smoothing) |
| Push notifications (mobile) | ❌ | ❌ | ✅ (native app + Firebase Cloud Messaging) |
| History | 1 month | 2 years | 6 months free / unlimited paid |
| Alert set points | 2 | Unlimited | Unlimited |
| Alert recipients | 1 | Multiple | Multiple |
| CSV export | ❌ | ✅ | ✅ |
| Modern app (iOS/Android) | ❌ (web only) | ❌ (web only) | ✅ (React Native or PWA) |
| Hardware price | $300 | $300 | $149–199 |
| Subscription | — | $37/yr | $99/yr (with prediction, trends) |

### Marketing Angle
- **"Everything they charge extra for, we include."** Gallons, charts, multiple alerts — all free with the hardware.
- **Software-first** — modern phone app with push notifications, smooth animations, dark mode. PTLevel looks like 2005 enterprise software.
- **More reliable sensor** — submersible pressure transducer eliminates the air-tube waterlogging problem that plagues PTLevel.
- **Single unit at the tank** — no indoor receiver box. Direct WiFi to your router, dashboard on your phone.
- **Predictive features** (paid tier) — "You'll run out in 12 days at current usage." PTLevel doesn't do this at all.

---

## Phase 0 — Brand & Domain (cost: ~$12/yr)

Pick a product name and register the domain. Needed before PCB silkscreen, labels, app, and marketing.

### Candidates (researched April 2026)

| Name | Domain Available? | Notes |
|------|-------------------|-------|
| **TankPulse** | Likely yes | tankpulse.com appears dead. Universal — works for any tank type. |
| **RanchFlow** | Likely yes | ranchflow.com appears dead. Wyoming ranch vibe but limits market. |
| **Brimm** | Maybe | brimm.com returned nothing — could be parked. Also a vintage cleaning brand name. |
| **WellSight** | No | WellSight Systems Inc. (geological software, Calgary). |
| **CisternIQ** | No | cisterniq.com is a Shopify "Opening soon" store — someone is building this exact product. |
| **Nivel** | No | Large vehicle parts company (50+ years). |
| **HeadWater** | No | Headwater Holidays (UK travel company since 1985). |
| **AquaPulse** | Risky | Generic water name, likely used by pool/irrigation products. |
| **SpringBox** | Risky | Common name used by agencies and subscription box services. |

### Action Items
- [ ] Pick a name
- [ ] Register `.com` domain (~$12/yr via Namecheap, Cloudflare, or Google Domains)
- [ ] Grab matching social handles (Twitter/X, Instagram)
- [ ] Use name on PCB silkscreen, enclosure label, dashboard, and app

---

## Phase 1 — Multi-Device Software (cost: $0)

### Firestore Restructure
Current:
```
readings/{docId}          — all readings mixed together
config/calibration        — single global calibration
```
Target:
```
devices/{deviceId}/readings/{docId}
devices/{deviceId}/config/calibration
users/{uid}/devices[]     — array of device IDs owned by this user
```

### Firmware Changes
- Read `machine.unique_id()`, hex-encode last 4 bytes → device_id (e.g. `a3f29bc1`)
- Include `device_id` field in every Firestore POST
- POST to `devices/{device_id}/readings` instead of `readings`
- Read calibration from `devices/{device_id}/config/calibration`

### Dashboard Changes
- Add Firebase Auth (email/password or Google sign-in)
- Read device ID from URL param: `?device=a3f29bc1`
- Load calibration from `devices/{device_id}/config/calibration`
- Fetch readings from `devices/{device_id}/readings`
- PWA manifest (Add to Home Screen on iOS/Android)

### Firestore Security Rules
```
match /devices/{deviceId}/readings/{doc} {
  allow create: if request.resource.data.device_id == deviceId;
  allow read: if deviceId in get(/databases/$(database)/documents/users/$(request.auth.uid)).data.devices;
}
```

---

## Phase 2 — PCB Design (cost: $800–1,500)

### Upwork Job Posting
> "Need a 2-layer PCB designed in KiCad for an IoT water level monitor.
>
> Components:
> - ESP32-S3-WROOM-1 module (pre-certified, FCC modular grant)
> - ADS1115 (MSOP-10) — 16-bit ADC for 4-20mA current loop
> - 220Ω 0.1% precision shunt resistor
> - TVS diode on sensor input (surge/ESD protection)
> - P-FET reverse polarity protection on 5V input
> - Resettable polyfuse on 5V input
> - AMS1117-3.3 or AP2112K LDO (3.3V regulator)
> - USB-C connector with ESD protection (for debug/programming)
> - 2-pin screw terminal for 5V power input
> - 2-pin screw terminal for 4-20mA sensor
> - Status LED (power + activity)
> - Test points for QC
>
> Deliverables: KiCad project files, BOM (JLCPCB parts), Gerbers.
> Board size: fit inside Hammond 1554K enclosure (160x90mm usable). Enclosure also houses RS-15-5 power supply. One 1/2" knockout for conduit entry (120VAC power) and one PG7 cable gland for sensor wire.
> Must follow ESP32-S3-WROOM antenna clearance guidelines."

### BOM (per unit, qty 100+)

| Component | Part | Unit Cost |
|---|---|---|
| ESP32-S3-WROOM-1 (N16R8) | Espressif | $3.00 |
| ADS1115 MSOP-10 | Texas Instruments | $4.50 |
| 220Ω 0.1% shunt | Yageo | $0.15 |
| TVS diode (SMAJ5.0A) | Littelfuse | $0.20 |
| P-FET (SI2301) | Vishay | $0.10 |
| Polyfuse 500mA | Bourns | $0.15 |
| LDO 3.3V (AP2112K) | Diodes Inc | $0.25 |
| USB-C connector | various | $0.30 |
| ESD protection (USBLC6-2) | STMicro | $0.20 |
| Screw terminals (2x) | Phoenix Contact | $0.40 |
| Status LED + resistor | various | $0.05 |
| PCB (4-layer, JLCPCB) | — | $1.50 |
| Passives (caps, resistors) | — | $0.30 |
| **Board subtotal** | | **~$11** |

### Enclosure & Assembly

| Item | Unit Cost |
|---|---|
| Hammond 1554K (IP66 ABS, 160×90×60mm) | $9.00 |
| 1/2" knockout (for conduit from junction box) | $0.50 |
| PG7 cable gland (sensor wire) | $0.50 |
| Product label (QR code, SN, specs) | $0.50 |
| Assembly labor (per unit) | $2.00 |
| RS-15-5 power supply (inside enclosure) | $8.00 |
| **Enclosure subtotal** | **~$21** |

### External Components (shipped with kit)

| Item | Unit Cost |
|---|---|
| Pressure sensor, 4-20mA, 5m range, cable | $18.00 |
| Wire nuts, 1/2" conduit, instructions | $3.00 |
| **External subtotal** | **~$21** |

### Total Per-Unit Cost (qty 100+): ~$54

---

## Phase 2.5 — Production Flashing & Provisioning

### Golden Image Approach
1. Build one board, flash MicroPython + all firmware files, verify it works
2. Dump the entire flash to a binary:
   ```bash
   picotool save -a golden.uf2          # Pico W
   esptool.py read_flash 0 0x400000 golden.bin  # ESP32-S3
   ```
3. Burn onto every new board:
   ```bash
   picotool load golden.uf2             # Pico W — ~5 seconds
   esptool.py write_flash 0 golden.bin  # ESP32-S3 — ~10 seconds
   ```

Every unit gets identical firmware. Per-device identity comes from `machine.unique_id()` at runtime (hardware-burned, no per-unit config needed). WiFi creds are set by the customer via provisioning (captive portal or BLE).

### Flash Script (batch production)
```bash
#!/bin/bash
# flash.sh — run for each unit on the bench
set -e
PORT=${1:-$(ls /dev/cu.usbmodem* 2>/dev/null | head -1)}
[[ -z "$PORT" ]] && echo "No device found" && exit 1

echo "Flashing $PORT..."
esptool.py --port "$PORT" write_flash 0 golden.bin
sleep 2

# Read back device ID for label printing
DEVICE_ID=$(python3 -c "
import serial, time
s = serial.Serial('$PORT', 115200, timeout=3)
s.write(b'\x03\x03')
time.sleep(1)
s.write(b'import machine,ubinascii; print(ubinascii.hexlify(machine.unique_id()).decode()[-8:])\r\n')
time.sleep(1)
out = s.read(4096).decode()
for line in out.splitlines():
    if len(line) == 8 and all(c in '0123456789abcdef' for c in line):
        print(line); break
s.close()
")
echo "Device ID: $DEVICE_ID"
echo "$DEVICE_ID" >> flash_log.csv
# Feed to label printer (Brother QL-810W or similar via brother_ql CLI)
# brother_ql -b pyusb -m QL-810W -p usb://... print -l 29 <(qrencode -o - -s 6 "$DEVICE_ID")
echo "✓ Done"
```

### Production Test Jig (50+ units)
- **Pogo-pin fixture** — 3D-printed jig with spring-loaded pogo pins touching SWD pads + power
- Flash over SWD using OpenOCD or `pyocd` (no USB cable needed, faster)
- Operator presses board into jig → LED goes green when flash + self-test pass
- **Self-test on first boot:** firmware checks I2C bus for ADS1115, reads ADC noise floor, blinks LED pattern to indicate pass/fail
- Total per-unit time: ~15 seconds (flash + verify + label)

### Label Printing
- QR code encodes device ID (e.g. `a3f29bc1`)
- Printed on weatherproof label: device ID, QR, "Scan to set up"
- Brother QL-810W thermal printer (~$100) + `brother_ql` Python CLI
- Applied to enclosure lid during assembly

### Scaling Path

| Volume | Method | Per-Unit Time |
|--------|--------|---------------|
| 1–10 | USB cable + `mpremote cp` | ~2 min |
| 10–50 | Golden image + `esptool.py` script | ~15 sec |
| 50–500 | Pogo-pin jig + SWD flash + label printer | ~15 sec |
| 500+ | Contract manufacturer (JLCPCB SMT + pre-flashed modules) | ~0 sec (they do it) |

> At 500+ units, order ESP32-S3-WROOM modules pre-flashed from Espressif or use JLCPCB's MCU programming service ($0.03/unit). Ship pre-populated boards directly to your bench for enclosure assembly + sensor kit packing.

---

## Phase 3 — FCC Certification (cost: $3,000–5,000)

- Using ESP32-S3-WROOM with FCC modular grant (FCC ID: 2AC7Z-ESPWROOM)
- Only need **FCC Part 15B** (unintentional emitter) testing
- Full intentional radiator testing NOT required (covered by module grant)
- Pre-scan at local EMC lab: ~$500 (optional, recommended)
- Full test + filing: $3,000–5,000
- Timeline: 4–6 weeks

### Requirements for modular grant to apply:
- Follow Espressif's antenna clearance guidelines (10mm keepout)
- Use reference circuit for power decoupling
- Label product with: "Contains FCC ID: 2AC7Z-ESPWROOM"

---

## Phase 4 — ESP32 Firmware Port

### What changes:
- `import network` — WLAN API is identical
- `machine.unique_id()` — works the same, returns chip ID
- `machine.I2C()` — same API, different default pins (GPIO8/9)
- `urequests` — identical
- NTP sync — identical
- OTA — identical (HTTP GET from GitHub raw)

### What's new:
- BLE provisioning (ESP32 has built-in BLE)
  - Device boots in AP/BLE mode if no WiFi config
  - Customer's phone app sends WiFi creds over BLE
  - No USB needed for customer setup

### What stays the same:
- sensor.py (ADS1115 I2C driver)
- firebase.py (Firestore REST API)
- main.py loop logic
- ota.py
- log.py

---

## Pricing Strategy

| | Price |
|---|---|
| Hardware kit (board + sensor + PSU + enclosure) | $149–199 |
| Dashboard subscription | $9.99/mo or $99/yr |
| Professional installation (optional) | $150 |

### Margins at $149 kit + $9.99/mo:
- Hardware margin: $100/unit (67%)
- Software margin: $120/yr/customer (100% — Firebase free tier covers ~100 devices)
- Break-even on development: 50–70 units sold

---

## Device Identity

Each ESP32/Pico W has a factory-burned unique ID:
```python
import machine, ubinascii
device_id = ubinascii.hexlify(machine.unique_id()).decode()[-8:]
# e.g. "a3f29bc1"
```

- Hardware-guaranteed unique, no provisioning needed
- Printed on product label as QR code
- Customer scans QR in phone app to link device to their account
- Firestore path: `devices/a3f29bc1/readings/...`

---

## Timeline

| Week | Milestone |
|---|---|
| 1 | Multi-device Firestore + Firebase Auth + PWA |
| 1 | Post Upwork job for PCB design |
| 2–3 | PCB design delivered, order prototypes from JLCPCB |
| 3 | Port firmware to ESP32, test on ESP32-S3 DevKitC |
| 5 | Prototype boards arrive, assemble + test |
| 5 | BLE provisioning firmware |
| 6 | FCC pre-scan at local EMC lab |
| 7–12 | FCC certification |
| 12 | First production run (50 units) |
| 13 | Start selling |

---

## Files to Create/Modify

### Firmware (cistern/)
- `firebase.py` — add device_id to POST path and payload
- `main.py` — read machine.unique_id(), pass to firebase
- `boot.py` — no changes
- `sensor.py` — no changes (I2C pin config may change for ESP32)
- `config.py` — add DEVICE_ID (auto-generated from chip)

### Dashboard (cistern/dashboard/)
- `index.html` — add Firebase Auth, device URL param, per-device data loading

### Infrastructure (cistern/infrastructure/)
- `firebase.tf` — update Firestore rules for multi-device
- Firestore indexes for `devices/{id}/readings` ordered by timestamp

### Tests (cistern/tests/)
- `seed_calibration.py` — update for `devices/{id}/config/calibration` path
- `cleanup_firestore.py` — update for nested collection path
