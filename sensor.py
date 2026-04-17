# sensor.py - Water depth sensor via 220Ω shunt + ADS1115
# 4-20mA sensor -> 220Ω shunt -> 220Ω/220Ω voltage divider -> ADS1115 A0 (I2C)
# Shunt voltage: 0.88V (4mA) to 4.40V (20mA)
# After divider:  0.44V (4mA) to 2.20V (20mA) — safe for 3.3V ADS1115
# Software multiplies ADC reading by 2 to recover actual shunt voltage

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
    time.sleep(0.01)
    
    data = i2c.readfrom_mem(ADS1115_ADDR, REG_CONVERSION, 2)
    value = (data[0] << 8) | data[1]
    if value > 32767:
        value -= 65536
    return value


# Voltage divider ratio: 220Ω / (220Ω + 220Ω) = 0.5, so multiply by 2
DIVIDER_RATIO = 2.0


def read_voltage(channel=0):
    """Read voltage from ADS1115 channel, compensated for voltage divider"""
    raw = read_adc(channel)
    adc_voltage = raw * 4.096 / 32767
    voltage = adc_voltage * DIVIDER_RATIO
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
