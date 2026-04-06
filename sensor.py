# sensor.py - Water depth sensor via HW-685
# Current setup: HW-685 AOUT -> GP26 (Pico built-in ADC)
# Future upgrade: HW-685 -> ADS1115 (I2C) for 16-bit resolution

from machine import ADC, Pin

# Pico built-in ADC on GP26 (ADC0) - 12-bit, 0-3.3V
adc = ADC(Pin(26))

# Calibration - adjust these for your setup
V_MIN = 0.66      # Voltage at 4mA (0 depth)
V_MAX = 3.3       # Voltage at 20mA (max depth)
DEPTH_MAX = 5.0   # Sensor max depth in meters

# Pico ADC: 16-bit read (0-65535), 3.3V reference
ADC_MAX = 65535
ADC_VREF = 3.3


def read_voltage():
    """Read voltage from Pico ADC on GP26"""
    raw = adc.read_u16()
    voltage = (raw / ADC_MAX) * ADC_VREF
    return raw, voltage


def read_depth():
    """
    Read water depth from 4-20mA sensor via HW-685.
    Returns dict with raw, voltage, depth_m, depth_pct.
    """
    raw, voltage = read_voltage()
    
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
