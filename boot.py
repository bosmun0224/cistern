# boot.py - Runs before main.py
import network
import time
from provision import has_config

wlan = None

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
