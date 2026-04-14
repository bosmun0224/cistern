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

    # CPU temperature (internal sensor on ADC4)
    try:
        adc = ADC(4)
        raw = adc.read_u16()
        telemetry['cpu_temp'] = round(27 - (raw * 3.3 / 65535 - 0.706) / 0.001721, 1)
    except Exception:
        pass

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
    while True:
        try:
            data = read_sensor()
            telemetry = get_device_telemetry()
            data.update(telemetry)

            # Sanity check: skip posting if voltage is out of plausible range
            v = data['voltage']
            if v < 0.3 or v > 3.6:
                print(f"Voltage out of range ({v}V) — sensor disconnected?")
                blink(4, 0.15)
                time.sleep(READ_INTERVAL)
                continue

            print(f"Voltage: {data['voltage']}V | Raw: {data['raw']} | "
                  f"RSSI: {data.get('rssi', '?')}dBm | "
                  f"FreeMem: {data.get('free_mem', '?')}B")
            
            blink(1)  # Heartbeat
            
            post_reading(data)
            
        except Exception as e:
            print(f"Error reading sensor: {e}")
            blink(3, 0.2)  # Error blink
        
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
