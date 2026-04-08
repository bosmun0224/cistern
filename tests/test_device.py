# test_device.py — On-device smoke tests for Pico W
# Run with:  mpremote run tests/test_device.py
#
# Requires the Pico to be connected via USB and already provisioned
# (config.py must exist with WiFi + Firebase credentials).

import sys
import time

passed = 0
failed = 0
errors = []


def test(name, fn):
    global passed, failed
    try:
        result = fn()
        if result:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name}")
            failed += 1
            errors.append(name)
    except Exception as e:
        print(f"  FAIL  {name} — {e}")
        failed += 1
        errors.append(f"{name}: {e}")


# -------------------------------------------------------------------
# 1. Config
# -------------------------------------------------------------------
def test_config_exists():
    try:
        import config
        return True
    except ImportError:
        return False


def test_config_has_keys():
    import config
    required = ['WIFI_SSID', 'WIFI_PASSWORD', 'FIREBASE_PROJECT_ID',
                'FIREBASE_API_KEY', 'OTA_BASE_URL', 'OTA_FILES']
    for key in required:
        if not hasattr(config, key):
            print(f"         missing: {key}")
            return False
    return True


# -------------------------------------------------------------------
# 2. I2C / ADS1115
# -------------------------------------------------------------------
def test_i2c_scan():
    from machine import I2C, Pin
    i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)
    devices = i2c.scan()
    print(f"         devices: {[hex(d) for d in devices]}")
    return 0x48 in devices


def test_adc_read():
    from sensor import read_sensor
    data = read_sensor()
    v = data['voltage']
    raw = data['raw']
    print(f"         voltage={v}V  raw={raw}")
    return isinstance(raw, int) and isinstance(v, float)


def test_voltage_plausible():
    from sensor import read_sensor
    v = read_sensor()['voltage']
    # Should be between 0.3V and 3.6V if sensor is connected,
    # or near 0V if disconnected (still not negative or > 5V)
    return 0.0 <= v <= 5.0


# -------------------------------------------------------------------
# 3. WiFi
# -------------------------------------------------------------------
def test_wifi_connected():
    import network
    wlan = network.WLAN(network.STA_IF)
    return wlan.isconnected()


def test_wifi_rssi():
    import network
    wlan = network.WLAN(network.STA_IF)
    if not wlan.isconnected():
        return False
    rssi = wlan.status('rssi')
    print(f"         rssi={rssi} dBm")
    return -100 < rssi < 0


# -------------------------------------------------------------------
# 4. Firebase POST
# -------------------------------------------------------------------
def test_firebase_post():
    from sensor import read_sensor
    from firebase import post_reading
    data = read_sensor()
    data['rssi'] = -50  # dummy telemetry
    data['free_mem'] = 100000
    data['cpu_temp'] = 30.5
    result = post_reading(data)
    return result is True


# -------------------------------------------------------------------
# 5. OTA endpoint
# -------------------------------------------------------------------
def test_ota_version_reachable():
    import urequests
    from config import OTA_BASE_URL
    r = urequests.get(OTA_BASE_URL + "version.txt")
    ok = r.status_code == 200
    if ok:
        ver = r.text.strip()
        print(f"         remote version: {ver}")
    r.close()
    return ok


# -------------------------------------------------------------------
# 6. Device telemetry
# -------------------------------------------------------------------
def test_free_memory():
    import gc
    gc.collect()
    mem = gc.mem_free()
    print(f"         free_mem={mem} bytes")
    return mem > 0


def test_storage():
    import os
    st = os.statvfs('/')
    total = st[0] * st[2]
    free = st[0] * st[3]
    used_pct = ((total - free) / total) * 100
    print(f"         storage: {total} total, {used_pct:.0f}% used")
    return total > 0 and free > 0


def test_cpu_temp():
    from machine import ADC
    adc = ADC(4)
    raw = adc.read_u16()
    temp = round(27 - (raw * 3.3 / 65535 - 0.706) / 0.001721, 1)
    print(f"         cpu_temp={temp} °C")
    return 0 < temp < 85


# -------------------------------------------------------------------
# Run all
# -------------------------------------------------------------------
print("\n=== Cistern Device Smoke Tests ===\n")

print("[config]")
test("config.py exists", test_config_exists)
test("config has required keys", test_config_has_keys)

print("[hardware]")
test("I2C finds ADS1115 at 0x48", test_i2c_scan)
test("ADC returns raw + voltage", test_adc_read)
test("voltage in plausible range", test_voltage_plausible)

print("[wifi]")
test("WiFi connected", test_wifi_connected)
test("WiFi RSSI valid", test_wifi_rssi)

print("[firebase]")
test("POST reading to Firestore", test_firebase_post)

print("[ota]")
test("version.txt reachable", test_ota_version_reachable)

print("[telemetry]")
test("free memory > 0", test_free_memory)
test("storage readable", test_storage)
test("CPU temp in range", test_cpu_temp)

print(f"\n{'='*40}")
print(f"  {passed} passed, {failed} failed")
if errors:
    print(f"\n  Failures:")
    for e in errors:
        print(f"    - {e}")
print(f"{'='*40}\n")

sys.exit(0 if failed == 0 else 1)
