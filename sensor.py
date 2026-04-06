# sensor.py - Water depth sensor via HW-685 + ADS1115
# HW-685 AOUT -> ADS1115 A0 (I2C) -> Pico W (GP4/GP5)

from machine import I2C, Pin
import time

# I2C setup (Pico W: SDA=GP4, SCL=GP5)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)

# ADS1115 config
ADS1115_ADDR = 0x48
REG_CONVERSION = 0x00
REG_CONFIG = 0x01

# Calibration - adjust these for your setup
V_MIN = 0.66      # Voltage at 4mA (0 depth)
V_MAX = 3.3       # Voltage at 20mA (max depth)
DEPTH_MAX = 5.0   # Sensor max depth in meters


def scan_i2c():
    """Scan I2C bus for devices"""
    devices = i2c.scan()
    print(f"I2C devices found: {[hex(d) for d in devices]}")
    return devices


def read_adc(channel=0):
    """Read raw value from ADS1115 channel (0-3)"""
    config = [0xC0 | (channel << 4) | 0x03, 0x83]
    i2c.writeto_mem(ADS1115_ADDR, REG_CONFIG, bytes(config))
    time.sleep(0.01)
    
    data = i2c.readfrom_mem(ADS1115_ADDR, REG_CONVERSION, 2)
    value = (data[0] << 8) | data[1]
    if value > 32767:
        value -= 65536
    return value


def read_voltage(channel=0):
    """Read voltage from ADS1115 channel"""
    raw = read_adc(channel)
    voltage = raw * 4.096 / 32767
    return raw, voltage


def read_depth():
    """
    Read water depth from 4-20mA sensor via HW-685 and ADS1115.
    Returns dict with raw, voltage, depth_m, depth_pct.
    """
    raw, voltage = read_voltage(0)
    
    # Clamp to valid range
    v_clamped = max(V_MIN, min(V_MAX, voltage))
    
    # Linear conversion to depth
    depth_m = ((v_clamped - V_MIN) / (V_MAX - V_MIN)) * DEPTH_MAX
    depth_pct = (depth_m / DEPTH_MAX) * 100
    
    return {
        'raw': raw,
        'voltage': round(voltage, 3),
        'depth_m': round(depth_m, 2),
        'depth_pct': round(depth_pct, 1)
    }
