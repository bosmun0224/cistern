# main.py - Main application entry point
import time
from machine import Pin

from sensor import read_depth
from ota import check_for_updates

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


def main():
    print("\n=== Cistern Monitor ===")
    
    # Check for OTA updates
    print("\n--- OTA Check ---")
    check_for_updates(auto_reboot=True)
    
    # Main loop
    print("\n--- Starting sensor loop ---")
    while True:
        try:
            data = read_depth()
            print(f"Depth: {data['depth_m']}m ({data['depth_pct']}%) | "
                  f"Voltage: {data['voltage']}V | Raw: {data['raw']}")
            
            blink(1)  # Heartbeat
            
            # TODO: Send data to server/cloud
            # post_reading(data)
            
        except Exception as e:
            print(f"Error reading sensor: {e}")
            blink(3, 0.2)  # Error blink
        
        time.sleep(READ_INTERVAL)


if __name__ == '__main__':
    main()
