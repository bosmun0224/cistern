# boot.py - Runs before main.py
import network
import time

try:
    from config import WIFI_SSID, WIFI_PASSWORD
except ImportError:
    print("ERROR: config.py not found. Copy config.py.example to config.py")
    WIFI_SSID = None
    WIFI_PASSWORD = None

wlan = None

def connect_wifi():
    global wlan
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

# Connect on boot
connect_wifi()
