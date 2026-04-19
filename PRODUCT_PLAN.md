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
> Board size: fit inside Hammond 1554B enclosure (65x65mm usable).
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
| Hammond 1554B (IP66 ABS) | $6.00 |
| PG7 cable glands (x2) | $1.00 |
| Product label (QR code, SN, specs) | $0.50 |
| Assembly labor (per unit) | $2.00 |
| **Enclosure subtotal** | **~$10** |

### External Components (shipped with kit)

| Item | Unit Cost |
|---|---|
| RS-15-5 power supply (120VAC → 5VDC, UL listed) | $8.00 |
| Pressure sensor, 4-20mA, 5m range, cable | $18.00 |
| Wire nuts, cable, instructions | $2.00 |
| **External subtotal** | **~$28** |

### Total Per-Unit Cost (qty 100+): ~$49

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
