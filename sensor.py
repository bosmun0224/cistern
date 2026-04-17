# sensor.py - Water depth sensor via 220Ω shunt + ADS1115
# 4-20mA sensor -> two 220Ω resistors in series -> ADS1115 reads midpoint
# ADC sees: I × 220Ω (bottom resistor) = 0.88V (4mA) to 4.40V (20mA)
# Tank height limits practical max to ~1.91V (~8.7mA)

from machine import I2C, Pin
import time

# I2C setup (Pico W: SDA=GP4, SCL=GP5)
i2c = I2C(0, scl=Pin(5), sda=Pin(4), freq=400000)

# ADS1115 config
ADS1115_ADDR = 0x48
REG_CONVERSION = 0x00
REG_CONFIG = 0x01


def scan_i2c():
    """Scan I2C bus for devices"""
    devices = i2c.scan()
    print(f"I2C devices found: {[hex(d) for d in devices]}")
    return devices


def read_adc(channel=0):
    """Read raw value from ADS1115 channel (0-3)"""
    config = [0xC0 | (channel << 4) | 0x03, 0x83]
    i2c.writeto_mem(ADS1115_ADDR, REG_CONFIG, bytes(config))
    # Poll conversion-ready bit instead of fixed sleep
    for _ in range(20):
        time.sleep_ms(1)
        cfg = i2c.readfrom_mem(ADS1115_ADDR, REG_CONFIG, 2)
        if (cfg[0] << 8 | cfg[1]) & 0x8000:
            break
    
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


def read_sensor():
    """
    Read raw sensor data from ADS1115.
    Returns dict with raw ADC value and voltage.
    All depth/volume computation is done on the dashboard.
    """
    raw, voltage = read_voltage(0)
    return {
        'raw': raw,
        'voltage': round(voltage, 4),
    }
