# main.py - Main application entry point
import time
import gc
import os
from machine import Pin, ADC

from sensor import read_sensor, scan_i2c
from ota import check_for_updates
from firebase import post_reading

# Onboard LED for status
led = Pin('LED', Pin.OUT)

# Reading interval in seconds
READ_INTERVAL = 60

# Re-sync NTP every 6 hours (in loop iterations)
NTP_SYNC_INTERVAL = (6 * 3600) // READ_INTERVAL

# Check for OTA updates every hour (in loop iterations)
OTA_CHECK_INTERVAL = (1 * 3600) // READ_INTERVAL

# WiFi reconnect settings
WIFI_MAX_RETRIES = 5
WIFI_RETRY_DELAY = 10

# Max readings to buffer when Firebase is unreachable
SEND_BUFFER_MAX = 30


def blink(times=1, duration=0.1):
    """Blink onboard LED"""
    for _ in range(times):
        led.on()
        time.sleep(duration)
        led.off()
        time.sleep(duration)


def get_device_telemetry():
    """Gather device stats to send alongside sensor data."""
    import network
    telemetry = {}

    # Firmware version
    try:
        with open('version.txt', 'r') as f:
            telemetry['version'] = f.read().strip()
    except Exception:
        pass

    # WiFi RSSI
    try:
        wlan = network.WLAN(network.STA_IF)
        if wlan.isconnected():
            telemetry['rssi'] = wlan.status('rssi')
    except Exception:
        pass

    # Free memory
    gc.collect()
    telemetry['free_mem'] = gc.mem_free()

    # CPU temperature (Pico W reads via ADC4, same as regular Pico)
    try:
        temp_adc = ADC(4)
        raw = temp_adc.read_u16()
        voltage = raw * 3.3 / 65535
        telemetry['cpu_temp'] = round(27 - (voltage - 0.706) / 0.001721, 1)
    except Exception as e:
        print("CPU temp error: " + str(e))

    # Storage (flash filesystem)
    try:
        st = os.statvfs('/')
        block_size = st[0]
        total_blocks = st[2]
        free_blocks = st[3]
        telemetry['total_storage'] = block_size * total_blocks
        telemetry['used_storage'] = block_size * (total_blocks - free_blocks)
    except Exception:
        pass

    return telemetry


def ensure_wifi():
    """Check WiFi and reconnect if needed. Returns True if connected."""
    import network
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True
    
    print("WiFi disconnected, reconnecting...")
    wlan.active(True)
    
    try:
        from config import WIFI_SSID, WIFI_PASSWORD
    except ImportError:
        return False
    
    for attempt in range(1, WIFI_MAX_RETRIES + 1):
        print(f"  Attempt {attempt}/{WIFI_MAX_RETRIES}")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        timeout = 15
        while not wlan.isconnected() and timeout > 0:
            time.sleep(1)
            timeout -= 1
        if wlan.isconnected():
            print(f"  Reconnected: {wlan.ifconfig()[0]}")
            blink(2, 0.1)
            return True
        wlan.disconnect()
        if attempt < WIFI_MAX_RETRIES:
            time.sleep(WIFI_RETRY_DELAY)
    
    print("  WiFi reconnect failed")
    blink(6, 0.1)
    return False


def main():
    print("\n=== Cistern Monitor ===")
    print("(Ctrl+C to drop to REPL)\n")
    
    # Check I2C devices
    print("Scanning I2C bus...")
    devices = scan_i2c()
    if 0x48 not in devices:
        print("WARNING: ADS1115 not found at 0x48")
        blink(5, 0.2)
    
    # Check for OTA updates
    print("\n--- OTA Check ---")
    check_for_updates(auto_reboot=True)
    
    # Main loop
    print("\n--- Starting sensor loop ---")
    loop_count = 0
    ota_count = 0
    send_buffer = []
    while True:
        try:
            data = read_sensor()
            telemetry = get_device_telemetry()
            data.update(telemetry)

            # Sanity check: skip posting if voltage is out of plausible range
            v = data['voltage']
            if v < 0.3 or v > 3.3:
                print(f"Voltage out of range ({v}V) — sensor disconnected?")
                blink(4, 0.15)
                time.sleep(READ_INTERVAL)
                continue

            print(f"Voltage: {data['voltage']}V | Raw: {data['raw']} | "
                  f"RSSI: {data.get('rssi', '?')}dBm | "
                  f"FreeMem: {data.get('free_mem', '?')}B")
            
            blink(1)  # Heartbeat
            
            # Stamp reading time so buffered posts keep correct timestamp
            from firebase import _iso_timestamp, _iso_timestamp_offset
            data['_timestamp'] = _iso_timestamp()
            data['_expireAt'] = _iso_timestamp_offset(30)
            
            if ensure_wifi():
                # Flush buffered readings first
                if send_buffer:
                    print(f"  Flushing {len(send_buffer)} buffered reading(s)...")
                    still_failed = []
                    for buffered in send_buffer:
                        if not post_reading(buffered):
                            still_failed.append(buffered)
                            break  # stop flushing on first failure
                    send_buffer = still_failed

                if not post_reading(data):
                    print("  Firebase post failed, buffering")
                    send_buffer.append(data)
            else:
                print("  No WiFi — buffering reading")
                send_buffer.append(data)
            
            # Cap buffer to prevent OOM
            if len(send_buffer) > SEND_BUFFER_MAX:
                dropped = len(send_buffer) - SEND_BUFFER_MAX
                send_buffer = send_buffer[-SEND_BUFFER_MAX:]
                print(f"  Buffer full, dropped {dropped} oldest reading(s)")
            
        except Exception as e:
            print(f"Error reading sensor: {e}")
            blink(3, 0.2)  # Error blink
        
        loop_count += 1
        ota_count += 1
        if loop_count >= NTP_SYNC_INTERVAL:
            loop_count = 0
            try:
                import ntptime
                ntptime.settime()
            except Exception:
                pass

        if ota_count >= OTA_CHECK_INTERVAL:
            ota_count = 0
            try:
                check_for_updates(auto_reboot=True)
            except Exception as e:
                print(f"OTA check failed: {e}")
        
        time.sleep(READ_INTERVAL)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n*** Ctrl+C — stopped. You're in the REPL. ***")
        print("Useful commands:")
        print("  from sensor import read_sensor, scan_i2c")
        print("  scan_i2c()          # list I2C devices")
        print("  read_sensor()       # take a sensor reading")
        print("  import machine; machine.reset()  # reboot")
