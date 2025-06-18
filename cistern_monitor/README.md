# Cistern Water Level Monitor

## Overview

This project monitors the water level in a cistern using a water level sensor connected to a Raspberry Pi via an Analog-to-Digital Converter (ADC). When the water level drops below a configurable threshold, the system sends an email alert.

The current version uses placeholder functions for sensor reading, so actual hardware integration is required for real-world use.

## Hardware Prerequisites

*   **Raspberry Pi:** Any model with GPIO pins (e.g., Raspberry Pi 3, 4, Zero).
*   **Water Level Sensor:** A sensor that can output a variable analog signal based on water height (e.g., TL-136, or a float sensor connected to a potentiometer).
*   **Analog-to-Digital Converter (ADC):** Required to convert the analog signal from the sensor to a digital value the Raspberry Pi can read. Common choices include:
    *   MCP3008 (10-bit ADC)
    *   MCP3208 (12-bit ADC)
*   **Jumper Wires & Breadboard:** For connecting the components.

## Software Prerequisites

*   Python 3.x
*   `pip` for Python package installation.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <your_repository_url_here>
    cd cistern_monitor
    ```
    (Replace `<your_repository_url_here>` with the actual URL of this repository).

2.  **Install dependencies:**
    It's recommended to use a Python virtual environment.
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows use `.\.venv\Scripts\activate`
    pip install -r requirements.txt
    ```

## Configuration (`app/config.py`)

All application settings are located in `app/config.py`. You **must** edit this file to match your setup.

*   `ADC_CHANNEL = 0`
    *   The specific channel on your ADC chip that the water level sensor is connected to (e.g., CH0 on an MCP3008).

*   `TANK_HEIGHT_CM = 200.0`
    *   The total height of your water tank in centimeters. This is used to calculate the water depth from the sensor's reading.

*   `ADC_MAX_VALUE = 1023`
    *   The maximum raw value your ADC can output.
    *   For a 10-bit ADC (like MCP3008), this is `1023` (2^10 - 1).
    *   For a 12-bit ADC (like MCP3208), this is `4095` (2^12 - 1).

*   `WATER_DEPTH_THRESHOLD_CM = 50.0`
    *   The water depth in centimeters. If the measured depth falls below this value, an alert email will be sent.

*   `READ_INTERVAL_SECONDS = 300`
    *   The time interval in seconds between consecutive sensor readings. For example, `300` means the system checks the water level every 5 minutes.

### Email Settings:

*   `SMTP_SERVER = "localhost"`
    *   Address of your SMTP (email) server. Example: `"smtp.gmail.com"`.

*   `SMTP_PORT = 1025`
    *   Port for your SMTP server. Common ports:
        *   `587` (TLS encryption)
        *   `465` (SSL encryption)
        *   `25` (unencrypted, not recommended)
        *   `1025` (for local debugging server, see "Testing" section).

*   `SMTP_USER = "your_email@example.com"`
    *   Username for authenticating with your SMTP server.

*   `SMTP_PASSWORD = "your_password"`
    *   **SECURITY WARNING:** Storing passwords directly in configuration files is insecure.
    *   For **Gmail/Google Workspace**: If you use 2-Step Verification, you **must** generate an "App Password" for this application. Your regular password will not work.
    *   For other email providers, check their documentation for SMTP access and app-specific passwords.
    *   **Recommendation:** Use environment variables or a secrets management system to handle sensitive credentials in a production environment.

*   `FROM_EMAIL = "cistern.alerts@example.com"`
    *   The email address that alerts will be sent *from*. Some SMTP servers require this to be the same as `SMTP_USER`.

*   `TO_EMAIL = "user_to_notify@example.com"`
    *   The email address where alert notifications will be sent.

### Sensor Calibration Note

The `convert_to_depth` function in `app/sensor.py` currently uses a simple linear conversion: `depth_cm = (adc_value / adc_max_value) * tank_height_cm`. This assumes the sensor's output is directly and linearly proportional to the water height from the very bottom to the very top of the tank.

**This will likely require calibration for your specific sensor and tank setup.**

**Steps for basic calibration:**

1.  **Identify Sensor Behavior:**
    *   Does the ADC value increase or decrease as the water level rises?
    *   Is the sensor placed at the bottom of the tank (measuring water height directly) or at the top (measuring distance to water)? The current formula assumes sensor at the bottom.

2.  **Measure ADC Readings at Known Depths:**
    *   With the tank empty (or at a known minimum water level), record the `adc_value` reported by `read_adc_value` (you might need to temporarily modify `main.py` to print this and run it).
    *   With the tank full (or at a known maximum water level), record the `adc_value`.
    *   Optionally, take readings at intermediate known depths.

3.  **Adjust Conversion Logic:**
    *   You may need to modify the formula in `app/sensor.py`'s `convert_to_depth` function.
    *   For example, if your sensor output is inverted (e.g., higher ADC value means lower water), you might use something like:
        `depth_cm = tank_height_cm - ((adc_value / adc_max_value) * tank_height_cm)`
    *   If there's an offset (e.g., empty doesn't read as 0 ADC), you'll need to subtract that offset:
        `calibrated_adc = adc_value - ADC_EMPTY_VALUE`
        `percentage_full = calibrated_adc / (ADC_FULL_VALUE - ADC_EMPTY_VALUE)`
        `depth_cm = percentage_full * tank_height_cm`
        (You'd need to define `ADC_EMPTY_VALUE` and `ADC_FULL_VALUE` in `config.py` after measuring them).

## Running the Application

Ensure you have configured `app/config.py` correctly.

To run the application:
```bash
python -m app.main
```
Alternatively, from the project root directory (`cistern_monitor`):
```bash
python app/main.py
```
The `-m` flag tells Python to run the module `app.main` as a script, which is often more robust for package structures.

## Hardware Integration Notes

The current `app/sensor.py` file contains **placeholder functions** for reading from an ADC:
*   `read_adc_value(adc_channel)`: Returns a dummy value.
*   `convert_to_depth(...)`: Performs a basic linear conversion.

You **must** replace the content of `read_adc_value` with code that interfaces with your actual ADC hardware.

**Example for MCP3008 ADC:**
You can use a library like `Adafruit-CircuitPython-MCP3xxx`.
1.  Install the library (it should be in `requirements.txt`):
    `pip install Adafruit-CircuitPython-MCP3xxx`
2.  Modify `app/sensor.py` to use it. See the library's documentation for specific examples.
    *   Link to library: [Adafruit CircuitPython MCP3xxx Library](https://github.com/adafruit/Adafruit_CircuitPython_MCP3xxx)

A typical integration would involve:
*   Importing the library.
*   Initializing the SPI bus and the MCP3008 chip.
*   Reading the analog value from the specified channel.

## Testing

This section outlines various ways to test the Cistern Water Level Monitor application, from individual components to the integrated system.

### Unit Testing `app/notifications.py` (Email Sending)

The `app/notifications.py` module contains a `if __name__ == '__main__':` block that allows you to test the `send_email` function directly.

**Using a Local SMTP Debugging Server:**
Before relying on real email alerts, it's highly recommended to test with a local SMTP debugging server. This server will print email contents to the console instead of attempting to send them over the internet.

1.  **Start the debug server:**
    Open a new terminal window and run:
    ```bash
    python -m smtpd -c DebuggingServer -n localhost:1025
    ```
    This server will listen on `localhost` port `1025`.

2.  **Configure for the debug server:**
    *   If running `app/notifications.py` directly: Modify the placeholder SMTP details in its `if __name__ == '__main__':` block.
    *   If testing through `app/main.py`: Edit `app/config.py` and set:
        ```python
        SMTP_SERVER = "localhost"
        SMTP_PORT = 1025
        SMTP_USER = "testuser"  # Can usually be anything for a local debug server
        SMTP_PASSWORD = "testpassword" # Can usually be anything
        TO_EMAIL = "recipient@example.com" # A test recipient
        ```

3.  **Run the notification script directly (for isolated testing):**
    ```bash
    python app/notifications.py
    ```
    Check the console output of `app/notifications.py` for success or error messages.
    Check the console output of the `DebuggingServer` - the email content should be printed there.

4.  Once testing is successful, remember to revert your `app/config.py` to your actual email provider's settings if you changed it for this test.

### Testing `app/sensor.py` (Post-Hardware Integration)

Testing the sensor module effectively requires that you have completed the hardware integration (i.e., replaced placeholder functions in `app/sensor.py` with actual ADC reading code).

*   **Testing `read_adc_value()`:**
    *   With your sensor connected to the ADC, run a modified version of `app/sensor.py` (or `app/main.py`) that prints the raw ADC values.
    *   Verify these readings against expected values. For example, if your sensor outputs a voltage, you can use a multimeter to measure the voltage at the ADC input pin and compare it to the ADC's digital output.
    *   Check readings at different water levels (e.g., sensor fully submerged, partially submerged, not in water).

*   **Calibrating and Testing `convert_to_depth()`:**
    *   Follow the steps in the "Sensor Calibration Note" section above. This is an iterative process:
        1.  Take ADC readings at known water depths (e.g., empty tank, full tank, and a few intermediate, measured points).
        2.  Adjust the conversion logic in `app/sensor.py` or related parameters in `app/config.py` (like `TANK_HEIGHT_CM`, or new calibration values like `ADC_EMPTY_VALUE`, `ADC_FULL_VALUE` if you implement them).
        3.  Re-run the application to see the calculated `current_depth_cm` and compare it against your manually measured depths.
        4.  Repeat until the calculated depth is accurate enough for your needs.

### Integration Testing `app/main.py` (Post-Hardware Integration & Calibration)

Once the sensor is integrated and calibrated, and email notifications are tested individually, you can test the main application loop.

1.  **Adjust Read Interval (Optional):** For quicker feedback during testing, you can temporarily lower `config.READ_INTERVAL_SECONDS` in `app/config.py` (e.g., to `10` seconds). Remember to set it back to a reasonable value for normal operation.

2.  **Normal Condition Test:**
    *   Ensure your physical setup (or simulated sensor input if you've built that capability into your hardware integration) represents a water level *above* `config.WATER_DEPTH_THRESHOLD_CM`.
    *   Run `python -m app.main`.
    *   **Expected Outcome:**
        *   The console should log messages indicating the water level is normal.
        *   No email alert should be sent.

3.  **Alert Condition Test:**
    *   Ensure your physical setup (or simulated sensor input) represents a water level *below* `config.WATER_DEPTH_THRESHOLD_CM`.
    *   Run `python -m app.main`.
    *   **Expected Outcome:**
        *   The console should log messages indicating the water level is below the threshold.
        *   An email alert should be sent (check your recipient inbox or the local SMTP debug server console).
        *   The console should log whether the email was sent successfully or if an error occurred.

4.  **Monitor Console Output:** Throughout these tests, check the console output from `app/main.py` for:
    *   Correct reporting of raw ADC values and calculated depth.
    *   Status messages from the application logic.
    *   Any error messages.

### Error Handling Tests (Conceptual)

These tests help ensure the application behaves gracefully when things go wrong.

*   **SMTP Error Handling:**
    *   Temporarily modify `SMTP_PASSWORD` or `SMTP_SERVER` in `app/config.py` to be invalid.
    *   Trigger an alert condition in `app/main.py`.
    *   **Expected Outcome:** The `send_email` function in `app/notifications.py` should catch the SMTP error, print an error message, and return `False`. `app/main.py` should then report that the email failed to send, but the main loop should continue to operate.

*   **Sensor Failure (Post-Hardware Integration):**
    *   Once you have real sensor code, consider what happens if the sensor or ADC fails (e.g., ADC disconnected from SPI bus, sensor wire breaks).
    *   Your hardware interaction code in `app/sensor.py` should ideally include `try-except` blocks to catch common hardware exceptions (e.g., `IOError`) and return a specific error code or raise a custom exception.
    *   `app/main.py`'s main loop already has a general `try-except Exception` block, but you might want more specific error handling for sensor failures (e.g., skip notification attempts if sensor reading failed).

Remember to revert any temporary configuration changes after testing.
