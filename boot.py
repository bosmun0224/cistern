# boot.py - Runs before main.py
import network
import time
from machine import Pin
from provision import has_config

wlan = None

# --- USB REPL debug escape hatch ---
# Hold GP15 low at boot (jumper GP15 to GND) to skip all code and drop
# straight into the MicroPython REPL for hardware troubleshooting.
# Alternatively, press Ctrl+C during the 3-second boot delay.
DEBUG_PIN = Pin(15, Pin.IN, Pin.PULL_UP)

def check_debug_mode():
    """Check if debug jumper is set (GP15 pulled to GND)."""
    if DEBUG_PIN.value() == 0:
        print("\n*** DEBUG MODE — GP15 held low ***")
        print("Dropping to REPL. Remove jumper and reset to boot normally.\n")
        return True
    return False

print("\n=== Cistern Boot ===")
print("Press Ctrl+C within 3s for REPL, or jumper GP15->GND for debug mode...")

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
        print(f"NTP synced: {t[0]:04d}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} UTC")
    except Exception as e:
        print(f"NTP sync failed: {e}")

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
    
    if wlan.isconnected():
        print(f"Already connected: {wlan.ifconfig()[0]}")
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
        print(f"Connected: {wlan.ifconfig()[0]}")
        sync_ntp()
        return True
    else:
        print("WiFi connection failed")
        return False

# Boot flow
if has_config():
    if not connect_wifi():
        # WiFi creds exist but connection failed — start provisioning
        print("Connection failed, starting setup mode...")
        from provision import run_server
        run_server()
else:
    # No config — start provisioning
    print("No WiFi configured, starting setup mode...")
    from provision import run_server
    run_server()
