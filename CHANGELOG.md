# Changelog

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
