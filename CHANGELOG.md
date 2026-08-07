# Changelog

## [1.15.0] - 2026-08-07

Fixes a silent multi-week outage: the device stopped posting on 2026-07-08 and did
not report again until it was physically power-cycled on 2026-08-04, leaving a
27-day hole in Firestore. Every reading in that history carries
`reset_cause = 1` (PWRON_RESET) and `crash_reports` is empty, so the device was
not crashing — it was hung, and nothing on board could recover it.

- Fix: **socket timeout on every network request.** `urequests` has no default
  timeout, so a half-open connection (a stale NAT entry after an AP reboot) blocks
  the socket read forever and freezes the main loop. Both `firebase.py` and
  `ota.py` now pass an explicit 5s timeout, with a safe fallback for older
  `urequests` builds that lack the kwarg. This is the root cause of the outage.
- Feat: **hardware watchdog** (`machine.WDT`, 8s). The existing software watchdog
  is checked at the top of the main loop, so it can never fire while the loop is
  blocked inside a socket read — precisely the failure that wedged the device.
  Armed only *after* the boot-time OTA check, because the RP2040 watchdog cannot
  be disabled once started; this keeps "power cycle → boot → OTA" as a recovery
  path that can never be caught in a reboot loop.
- Feat: watchdog feeding through every long-running path — the 60s inter-reading
  sleep, WiFi connect waits and retry delays, buffered-reading flushes, NTP sync,
  and between OTA file downloads. Request timeouts are deliberately shorter than
  the watchdog window so a stalled post buffers for retry rather than tripping a
  reboot.
- Fix: **`uptime_s` no longer wraps.** It reported `time.ticks_ms() // 1000`,
  which rolls over at 2^30 ms (~12.4 days), making reboots indistinguishable from
  wraps in telemetry. Now accumulates deltas via `ticks_diff`/`ticks_add`.
- Test: new `tests/test_reliability.py` covering request timeouts, the
  no-double-post fallback, and uptime monotonicity across a simulated 40-day run.
- Test: repaired the stale `test_sensor.py` I2C/time stubs, which had been failing
  since v1.13.2 added the ADS1115 general-call reset.

## [1.14.3] - 2026-05-14

- Fix: remove the VSYS ADC read added in 1.14.2. It sampled `machine.ADC(29)`,
  which on the Pico W is shared with the CYW43 wireless chip — reading it every
  60s intermittently crashed the WiFi stack.

## [1.14.2] - 2026-05-14

- Chore: log `vsys_v` and `current_ma` to diagnose the sensor undercurrent fault.
- Infra: allow `vsys_v` in the Firestore security-rule allowlist and telemetry payload.

## [1.14.1] - 2026-04-25

- Fix: OTA boot loop caused by `version.txt` failing the 10-byte minimum file size safety check (explicitly bypass the check for `version.txt`).

## [1.14.0] - 2026-04-25

- Fix: Critical memory fragmentation boot loop. Removed `from provision import has_config` in `boot.py` which was loading massive HTML strings into RAM and preventing `mbedtls` SSL handshakes from allocating memory.
- Feat: Hardware undercurrent fault detection. If sensor reads < 0.85V (< 4mA), it flashes the LED and posts "Undercurrent Fault" to telemetry, indicating power supply or sensor failure.
- Feat: Deep device telemetry tracking. Captures `alloc_mem` (heap usage), `uptime_s`, `reset_cause`, `wifi_reconnects`, and `loop_time_ms`.
- Feat: Fixed Pico W internal CPU temperature readings via 10-sample rolling average to filter CYW43 noise.
- Feat: Remote `crash.log` reporting. Any unhandled exception traceback in the main loop is saved to flash, then automatically uploaded to a `crash_reports` Firestore collection on the next boot.
- UI: Dashboard expanded with interactive telemetry boxes for Uptime, Reset Code, Reconnects, and Loop Time, complete with historical charting.
- Infra: Updated Terraform security rules to support the new telemetry keys and crash reporting collection.

## [1.13.2] - 2026-04-20

- Fix: add I2C general-call reset (0x06) before each ADS1115 read to prevent chip lockup/drift (per TI E2E recommendation)
- Fix: add dummy read before each ADS1115 conversion to flush stale charge from internal sample-and-hold capacitor
- Prevents slow voltage drift caused by residual charge accumulating across single-shot power-down cycles

## [1.13.1] - 2026-04-20

- Fix: clear last_error after successful Firebase post (prevents stale error in dashboard telemetry)

## [1.11.0] - 2026-04-17

- Provisioning now tests WiFi credentials before saving (STA+AP concurrent on CYW43)
- Shows spinner "Testing..." page, then auto-redirects to result
- On success: saves config, shows "Connected!" page, reboots
- On failure: shows specific error (wrong password / network not found / timed out) with "Try Again"
- Button renamed "Test & Save" — no more blind save-and-pray

## [1.10.0] - 2026-04-17

- WiFi hardening: enable CYW43 auto-reconnect (`reconnects=-1`) so firmware handles transient drops
- Set `PM_PERFORMANCE` power management — prevents power-save-induced disconnects
- Log specific WiFi failure reasons via `wlan.status()` (wrong password, no AP found, connect fail)
- Applies to both boot.py (initial connect) and main.py (runtime reconnect)

## [1.9.0] - 2026-04-17

- Field provisioning: jumper GP14 to GND at boot to force WiFi AP setup mode
- No USB needed — touch two pins, reboot, connect to AP, enter new WiFi creds

## [1.8.2] - 2026-04-17

- Fix: clear last_error after successful WiFi connect (prevents stale boot warnings)

## [1.8.1] - 2026-04-17

- Fix: OTA_FILES now defined in ota.py (not config.py) so new files propagate via OTA
- Removes stale OTA_FILES from config.py on next provisioning
- Prevents chicken-and-egg problem where config.py overrides ota.py's file list

## [1.8.0] - 2026-04-17

- Remote error visibility: last WARN/ERR included in every Firebase reading as `last_error`
- Dashboard shows last error in bottom-left corner (red text)
- No extra network calls — piggybacks on existing telemetry posts

## [1.7.0] - 2026-04-17

- Persistent file logging (log.py): writes to device.log on flash with auto-truncation at 16KB
- All key events logged: boot, WiFi, sensor reads, Firebase posts, OTA checks, errors
- Read logs via REPL: `log.read_log()` or `mpremote cat :device.log`
- Unhandled crashes logged before re-raise

## [1.6.1] - 2026-04-17

- Fix: buffered readings now keep their original timestamp instead of flush time

## [1.6.0] - 2026-04-17

- Buffer failed readings in memory and flush when connectivity returns
- Cap buffer at 30 readings (~30 min offline) to prevent OOM
- Stop flush on first failure to avoid hammering a dead connection

## [1.5.0] - 2026-04-17

- WiFi retry on boot: 3 attempts with 10s delay before falling back to provisioning
- WiFi reconnect in main loop: 5 attempts with 10s delay if connection drops
- Sensor readings continue even without WiFi (Firebase posts skipped until reconnected)

## [1.4.0] - 2026-04-17

- Show firmware version on dashboard (bottom-right corner)

## [1.3.0] - 2026-04-17

- Include firmware version in every Firebase reading
- Enforce strict Firestore field allowlist via `hasOnly` rules

## [1.2.0] - 2026-04-17

- Check for OTA updates every hour in main loop (no reboot needed)

## [1.1.0] - 2026-04-17

- Remove unnecessary `DIVIDER_RATIO = 2.0` — report actual ADC voltage
- Poll ADS1115 conversion-ready bit instead of fixed 10ms sleep
- Fix calibration values: v_min=0.88V, v_max=4.40V (actual ADC readings)
- Sanity bounds updated to 0.3–3.3V
- Add periodic NTP re-sync every 6 hours
- Replace incomplete URL decoder with generic `%XX` handler in provisioning
- Align `OTA_FILES` fallback default across ota.py, config.py.example, provision.py
- Escape quotes in WiFi credentials during provisioning
- Fix `~8mA` → `4mA` in README and seed_calibration.py

## [1.0.0] - 2026-04-08

- Initial release
- 4-20mA sensor reading via ADS1115 over I2C
- WiFi provisioning via captive portal
- Firebase Firestore integration with 30-day TTL
- OTA updates from GitHub on boot
- Web dashboard with tank visualization, charts, device telemetry
- Debug mode via GP15 jumper or Ctrl+C
- Terraform infrastructure for Firebase project
