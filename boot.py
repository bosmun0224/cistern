# boot.py - Runs before main.py
import network
import time
from machine import Pin
from provision import has_config
import log

wlan = None

# --- USB REPL debug escape hatch ---
# Hold GP15 low at boot (jumper GP15 to GND) to skip all code and drop
# straight into the MicroPython REPL for hardware troubleshooting.
# Alternatively, press Ctrl+C during the 3-second boot delay.
DEBUG_PIN = Pin(15, Pin.IN, Pin.PULL_UP)

# --- Field provisioning trigger ---
# Hold GP14 low at boot (jumper GP14 to GND) to force WiFi provisioning AP.
# Use this in the field to change WiFi SSID/password without USB.
PROVISION_PIN = Pin(14, Pin.IN, Pin.PULL_UP)

def check_debug_mode():
    """Check if debug jumper is set (GP15 pulled to GND)."""
    if DEBUG_PIN.value() == 0:
        print("\n*** DEBUG MODE — GP15 held low ***")
        print("Dropping to REPL. Remove jumper and reset to boot normally.\n")
        return True
    return False

def check_provision_mode():
    """Check if provisioning jumper is set (GP14 pulled to GND)."""
    if PROVISION_PIN.value() == 0:
        log.info('Provision jumper detected (GP14 low) — starting AP')
        return True
    return False

print("\n=== Cistern Boot ===")
print("Press Ctrl+C within 3s for REPL, or jumper GP15->GND for debug mode...")
log.info('Boot started')

if check_debug_mode():
    raise SystemExit  # Stops boot.py, skips main.py — lands in REPL

try:
    time.sleep(3)
except KeyboardInterrupt:
    print("\n*** Ctrl+C — dropping to REPL ***\n")
    raise SystemExit

def sync_ntp():
    """Sync RTC to NTP time."""
    try:
        import ntptime
        ntptime.settime()
        t = time.localtime()
        log.info(f'NTP synced: {t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} UTC')
    except Exception as e:
        log.warn(f'NTP sync failed: {e}')

def connect_wifi():
    global wlan
    
    try:
        from config import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        WIFI_SSID = None
        WIFI_PASSWORD = None
    
    if not WIFI_SSID:
        return False
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(pm=network.WLAN.PM_PERFORMANCE)
    
    if wlan.isconnected():
        log.info(f'Already connected: {wlan.ifconfig()[0]}')
        return True
    
    print(f"Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    timeout = 15
    while not wlan.isconnected() and timeout > 0:
        time.sleep(1)
        timeout -= 1
        print(".", end="")
    
    print()
    
    if wlan.isconnected():
        log.info(f'WiFi connected: {wlan.ifconfig()[0]}')
        log.last_error = None
        sync_ntp()
        return True
    else:
        status = wlan.status()
        reasons = {
            network.STAT_WRONG_PASSWORD: 'wrong password',
            network.STAT_NO_AP_FOUND: 'no AP found',
            network.STAT_CONNECT_FAIL: 'connect fail',
        }
        reason = reasons.get(status, f'status={status}')
        log.warn(f'WiFi connection failed: {reason}')
        wlan.disconnect()
        return False


def connect_wifi_with_retries(max_retries=3, delay=10):
    """Try to connect to WiFi multiple times before giving up."""
    for attempt in range(1, max_retries + 1):
        print(f"\nWiFi attempt {attempt}/{max_retries}")
        if connect_wifi():
            return True
        if attempt < max_retries:
            print(f"Retrying in {delay}s...")
            time.sleep(delay)
    return False


# Boot flow
if check_provision_mode():
    log.info('Forced provisioning mode via GP14 jumper')
    from provision import run_server
    run_server()
elif has_config():
    if not connect_wifi_with_retries():
        log.warn('All WiFi attempts failed, starting provisioning')
        from provision import run_server
        run_server()
else:
    log.info('No WiFi configured, starting provisioning')
    from provision import run_server
    run_server()
