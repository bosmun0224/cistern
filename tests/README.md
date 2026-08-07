# Tests

## Unit Tests (CPython)

Run from the `cistern/` directory:

```bash
python3 -m unittest tests.test_sensor tests.test_endpoints tests.test_reliability -v
```

| File | What it tests |
|------|---------------|
| `test_sensor.py` | ADC read shape, voltage→depth conversion, horizontal cylinder gallons formula |
| `test_endpoints.py` | Firestore REST API (valid post, missing field rejected, wrong type rejected, public read), GitHub OTA endpoint reachability |
| `test_reliability.py` | Network request timeouts, the no-double-post fallback for older `urequests`, and `uptime_s()` monotonicity across the `ticks_ms()` wrap |

> `test_endpoints.py` hits the live Firestore and GitHub raw endpoints, so it can
> fail with HTTP 429 if run repeatedly in quick succession. Wait a minute and
> re-run — the other two suites are offline and deterministic.

## On-Device Tests (MicroPython)

Plug in the Pico W via USB and run:

```bash
mpremote run tests/test_device.py
```

| Check | What it verifies |
|-------|-----------------|
| config | `config.py` exists with all required keys |
| hardware | I2C finds ADS1115 at 0x48, ADC returns valid data, voltage in range |
| wifi | Connected, RSSI is valid |
| firebase | POST a real reading to Firestore succeeds |
| ota | `version.txt` reachable on GitHub |
| telemetry | Free memory, storage, CPU frequency |

## Seed & Cleanup Scripts

```bash
python3 -m tests.seed_calibration     # Write /config/calibration doc (sensor + tank values)
python3 -m tests.seed_firestore       # Seed 288 readings (24h of 5-min intervals)
python3 -m tests.cleanup_firestore    # Delete all readings (uses gcloud auth)
```

| File | Purpose |
|------|---------|
| `seed_calibration.py` | Writes sensor/tank calibration to Firestore `/config/calibration` |
| `seed_firestore.py` | Seeds 288 test readings with realistic voltages + telemetry |
| `cleanup_firestore.py` | Deletes all documents from the `readings` collection |
