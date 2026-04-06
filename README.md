# Cistern Water Level Monitor

Remote cistern water level monitoring using a Raspberry Pi Pico W with OTA updates.

## Hardware

| Component | Purpose |
|-----------|---------|
| Pico W | Microcontroller with WiFi |
| 4-20mA depth sensor | Submersible pressure transducer |
| HW-685 | Current-to-voltage converter |
| ADS1115 | 16-bit ADC (I2C) |

## Wiring

```mermaid
graph LR
    subgraph USB Power
        USB[USB Micro<br>5V]
    end

    subgraph Pico W
        VBUS[VBUS - 5V]
        ADC0[GP26 / ADC0]
        GND1[GND]
        MCU[RP2040<br>+ WiFi]
    end

    subgraph HW-685
        VCC[VCC]
        AOUT[AOUT]
        GNDH[GND]
        IP[I+]
    end

    subgraph Sensor
        RED[Red Wire]
        BLK[Black Wire]
    end

    USB -->|5V| VBUS
    VBUS --> VCC
    GND1 --> GNDH
    RED --> VCC
    BLK --> IP
    AOUT --> ADC0
    ADC0 --- MCU
```

**Pin connections:**

| From | To |
|------|-----|
| Pico VBUS (5V) | HW-685 VCC |
| Pico GND | HW-685 GND |
| HW-685 AOUT | Pico GP26 |
| Sensor Red | HW-685 VCC |
| Sensor Black | HW-685 I+ |

## Setup

1. Flash MicroPython to your Pico W
2. Copy `config.py.example` to `config.py` and fill in your WiFi credentials
3. Upload all `.py` files to the Pico

```bash
pip install mpremote
mpremote cp boot.py main.py sensor.py ota.py config.py :
```

## OTA Updates

The Pico checks for updates on boot by comparing `version.txt` with the remote version.

To push an update:
1. Edit code in this repo
2. Bump `version.txt`
3. Push to GitHub
4. Pico downloads new files on next boot

## Files

| File | Purpose |
|------|---------|
| `boot.py` | WiFi connection on startup |
| `main.py` | Main loop |
| `sensor.py` | ADS1115 driver + depth calculation |
| `ota.py` | Over-the-air update logic |
| `config.py` | WiFi creds (gitignored) |
| `version.txt` | Current firmware version |

## Calibration

Edit `sensor.py` to match your sensor:

```python
V_MIN = 0.66      # Voltage at 4mA (empty)
V_MAX = 3.3       # Voltage at 20mA (full)
DEPTH_MAX = 5.0   # Sensor max depth in meters
```

## License

MIT
