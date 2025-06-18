# Cistern Water Level Monitor (Go Version)

## Overview

This project is a Go implementation of a cistern water level monitoring system. It's designed to run on a Raspberry Pi (or similar Linux-based SBC), read data from a water level sensor via an Analog-to-Digital Converter (ADC), and send email alerts when the water level drops below a configurable threshold.

This version currently uses **placeholder logic for actual sensor readings**, meaning it simulates ADC input. Hardware integration is required for real-world operation.

## Prerequisites

*   **Go:** Version 1.18 or newer is recommended. (Check with `go version`)
*   **Git:** For cloning the repository. (Check with `git --version`)

## Hardware Prerequisites

*   **Raspberry Pi:** Any model with GPIO and SPI capabilities (e.g., Raspberry Pi 3, 4, Zero W).
*   **Water Level Sensor:** An analog output sensor (e.g., TL-136, float sensor with potentiometer).
*   **Analog-to-Digital Converter (ADC):** A chip like the MCP3008 (10-bit SPI ADC) is commonly used. Ensure you have a Go library or can implement SPI communication for it.
*   **Jumper Wires & Breadboard:** For connecting the components.

## Project Structure

The project follows a standard Go project layout:

```
cistern-monitor-go/
├── cmd/cistern-monitor/   # Main application entry point
│   └── main.go
├── pkg/                   # Reusable library code
│   ├── config/            # Configuration loading and struct
│   │   └── config.go
│   ├── notifier/          # Email notification logic
│   │   └── notifier.go
│   └── sensor/            # Sensor reading and data conversion
│       └── sensor.go
├── go.mod                 # Go module definition
├── go.sum                 # Dependency checksums
└── README.md              # This file
```

## Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone <your_repository_url_here> cistern-monitor-go
    # Replace <your_repository_url_here> with the actual URL of this repository
    cd cistern-monitor-go
    ```

2.  **Tidy dependencies:**
    While this project currently uses only the standard library, it's good practice to run:
    ```bash
    go mod tidy
    ```
    This will ensure `go.mod` and `go.sum` are up-to-date if dependencies are added later.

## Configuration

Configuration is currently managed through **default values** set directly within the `LoadConfig()` function in `pkg/config/config.go`.

**You MUST review and update these default values to match your specific setup before running the application effectively.**

Key configuration parameters in the `config.Config` struct:

*   **Sensor Settings:**
    *   `ADCDevice` (string): Path to the SPI device for your ADC (e.g., `"/dev/spidev0.0"`). **Placeholder, actual hardware interaction needed.**
    *   `ADCChannel` (int): The ADC channel connected to your water sensor (e.g., `0` for CH0).
    *   `TankHeightCM` (float64): Total height of your water tank in centimeters.
    *   `ADCMaxValue` (int): The maximum raw value your ADC can output (e.g., `1023` for a 10-bit ADC like MCP3008, `4095` for 12-bit).

*   **Alerting Settings:**
    *   `WaterDepthThresholdCM` (float64): If the water depth falls below this value (in cm), an alert is sent.

*   **Application Behavior:**
    *   `ReadIntervalSeconds` (int): How often (in seconds) the system checks the water level.

*   **Email (SMTP) Settings:**
    *   `SMTPServer` (string): Address of your SMTP server (e.g., `"smtp.gmail.com"`).
    *   `SMTPPort` (int): Port for your SMTP server (e.g., `587` for TLS, `465` for SSL, `1025` for local debug).
    *   `SMTPUser` (string): Username for SMTP authentication.
    *   `SMTPPassword` (string): **SECURITY WARNING!** The default is a placeholder. Avoid hardcoding real passwords. For production, use environment variables, a secrets management tool, or prompt at startup. For Gmail/GSuite with 2FA, an "App Password" is required.
    *   `FromEmail` (string): The email address alerts will be sent from.
    *   `ToEmail` (string): The email address where alert notifications will be sent.

**Sensor Placeholder Note:**
The function `ReadRawADCValue()` in `pkg/sensor/sensor.go` is currently a **placeholder**. It returns a dummy value and does not interact with any hardware. You will need to implement the logic to read from your specific ADC using appropriate Go libraries for SPI communication (see "Hardware Integration Guidance" below).

## Building the Application

You can build the application for your local machine or cross-compile for your Raspberry Pi.

*   **Build for your current system (for local testing, not Pi):**
    ```bash
    go build -o cistern-monitor ./cmd/cistern-monitor
    ```
    (This creates an executable named `cistern-monitor` in the project root.)

*   **Cross-compiling for Raspberry Pi:**
    The exact flags depend on your Raspberry Pi model and the OS installed (32-bit or 64-bit).

    *   **For older Raspberry Pi models (Pi Zero, Pi 1 - ARMv6, 32-bit OS):**
        ```bash
        GOOS=linux GOARCH=arm GOARM=6 go build -ldflags="-s -w" -o cistern-monitor-rpi-armv6 ./cmd/cistern-monitor
        ```
    *   **For Raspberry Pi 2, 3, 4 (ARMv7, 32-bit OS):**
        ```bash
        GOOS=linux GOARCH=arm GOARM=7 go build -ldflags="-s -w" -o cistern-monitor-rpi-armv7 ./cmd/cistern-monitor
        ```
    *   **For Raspberry Pi 3, 4, Zero 2 W (ARMv8, 64-bit OS):**
        ```bash
        GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o cistern-monitor-rpi-arm64 ./cmd/cistern-monitor
        ```
    The `-ldflags="-s -w"` flag strips debug symbols and DWARF information, making the binary smaller. This is optional.

## Running the Application

1.  After building (and cross-compiling if necessary), transfer the executable (e.g., `cistern-monitor-rpi-arm64`) to your Raspberry Pi.
2.  Make it executable: `chmod +x ./cistern-monitor-rpi-arm64`
3.  Run it: `./cistern-monitor-rpi-arm64`

For long-term operation, you should run the application as a service (e.g., using `systemd`) or in a terminal multiplexer like `screen` or `tmux`:
```bash
nohup ./cistern-monitor-rpi-arm64 > cistern-monitor.log 2>&1 &
```

## Hardware Integration Guidance (Sensor)

As mentioned, `pkg/sensor/sensor.go` currently uses a placeholder for `ReadRawADCValue()`. To make the application functional, you need to:

1.  **Choose a Go library for SPI communication** with your ADC (e.g., MCP3008). Some options include:
    *   `periph.io/x/conn/v3/spi` (part of the Periph.io suite for hardware access)
    *   Other SPI or platform-specific GPIO/SPI libraries.
    You might need to add these to your `go.mod` file (`go get periph.io/x/conn/v3/spi`).

2.  **Implement `ReadRawADCValue()`:**
    *   Initialize the SPI connection to your ADC device (e.g., `"/dev/spidev0.0"`).
    *   Construct the command bytes to send to the ADC to request a reading from the configured channel (`s.ADCChannel`). This depends on the ADC's datasheet (e.g., for MCP3008, it involves sending start bits, single/differential mode bits, and channel select bits).
    *   Perform the SPI transaction (send command, receive data).
    *   Parse the received bytes to get the raw integer ADC value.
    *   Handle any errors during SPI communication.
    *   Return the raw ADC value and any error.

## Testing Strategy

Thorough testing is essential to ensure the reliability of the Cistern Water Level Monitor. This involves unit tests for individual packages and integration tests for the complete application.

### Unit Testing

Unit tests focus on isolating and verifying specific parts of the codebase.

*   **`pkg/config`:**
    *   Test `config.LoadConfig()`: Verify that it returns a `config.Config` struct populated with the expected default values. This can be done by checking each field of the returned struct.

*   **`pkg/sensor`:**
    *   **`sensor.ConvertToDepth(rawValue int) float64`:**
        *   Write test cases with various `rawValue` inputs (e.g., 0, `ADCMaxValue`/2, `ADCMaxValue`, values outside this range if applicable) and assert that the calculated depth is correct based on the `TankHeightCM` and `ADCMaxValue` set in the `Sensor` struct.
        *   Consider edge cases like `ADCMaxValue` being 0 (if not prevented at struct creation).
    *   **`sensor.ReadRawADCValue() (int, error)` (Post-Hardware Implementation):**
        *   Once implemented with real hardware logic, testing becomes more complex.
        *   **Mocking Hardware:** For automated tests, you would typically abstract the hardware interaction behind an interface and use a mock implementation of that interface to simulate different hardware responses (e.g., various ADC readings, error conditions like SPI failure).
        *   **Manual Hardware Tests:** Connect the actual sensor and ADC. Use a multimeter to verify the analog voltage from the sensor at different water levels and compare it with the digital value read by `ReadRawADCValue()`. Test with known sensor states (e.g., sensor dry, sensor fully submerged).

*   **`pkg/notifier`:**
    *   **`notifier.SendEmail(...)`:**
        *   **Local SMTP Debugging Server:** This is the primary way to test email sending without external dependencies.
            1.  Start a local SMTP debug server: `python -m smtpd -c DebuggingServer -n localhost:1025`
            2.  In your test code (or by temporarily modifying `pkg/config/config.go`), set the `EmailConfig` to use:
                ```go
                SMTPServer: "localhost",
                SMTPPort:   1025,
                SMTPUser:   "testuser", // Usually ignored by debug server
                SMTPPassword: "testpassword", // Usually ignored
                FromEmail: "sender@example.com",
                ```
            3.  Call `notifier.SendEmail` with a test recipient, subject, and body.
            4.  Assert that `SendEmail` returns `nil` (no error).
            5.  Check the console output of the `DebuggingServer` to verify the email content (headers and body) is correctly formatted and received.
        *   **Testing `SendEmailWithExplicitTLS`:** If using this function for production, similar tests can be done, but it's harder to mock a TLS-enabled SMTP server locally. Initial tests might still use the debug server (which won't use TLS), then test against a real staging/test email account on a provider like Gmail.
        *   **Mocking (Advanced):** For more isolated unit tests without any network calls, you could define an `EmailSender` interface and mock it. The current `SendEmail` function is a direct implementation, so this would require refactoring.

### Integration Testing (`cmd/cistern-monitor/main.go`)

Integration testing verifies that the different parts of the application work together correctly. This should ideally be performed after the hardware-specific code in `pkg/sensor` is implemented and calibrated.

1.  **Preparation:**
    *   Ensure the sensor is connected and (at least preliminarily) calibrated.
    *   Configure `pkg/config/config.go` with appropriate settings (especially for the sensor and a test email recipient, possibly using the local SMTP debug server).
    *   For faster feedback during testing, temporarily lower `ReadIntervalSeconds` in `config.go` (e.g., to `5` or `10` seconds). Remember to revert this for normal operation.

2.  **Normal Condition Test:**
    *   Arrange the physical setup so the water level is *above* the `WaterDepthThresholdCM`.
    *   Run the main application: `go run ./cmd/cistern-monitor` (or the compiled binary).
    *   **Expected Outcome:**
        *   The application logs should indicate normal water levels.
        *   No email alert should be sent. Check the SMTP debug server console if used.

3.  **Alert Condition Test:**
    *   Arrange the physical setup so the water level is *below* the `WaterDepthThresholdCM`.
    *   Run the main application.
    *   **Expected Outcome:**
        *   Application logs should indicate the water level is below the threshold.
        *   An email alert should be sent. Verify its content on the SMTP debug server or the test recipient's inbox.
        *   Logs should confirm the email sending attempt and its success or failure.

4.  **Monitor Application Logs:** Throughout these tests, closely observe the application's console output for:
    *   Correct reporting of (simulated or real) ADC values and calculated depths.
    *   Status messages indicating the application's state and actions.
    *   Any error messages.

### Error Handling Tests (Conceptual)

These tests verify how the application responds to failures.

*   **SMTP Errors:**
    *   Temporarily misconfigure SMTP settings in `pkg/config/config.go` (e.g., invalid `SMTPServer`, wrong `SMTPPort`, incorrect `SMTPPassword`).
    *   Trigger an alert condition.
    *   **Expected Outcome:** `notifier.SendEmail` should return an error. The main loop in `main.go` should log this error (e.g., "Failed to send alert email: ...") and continue its operation (i.e., it shouldn't crash).

*   **Sensor Errors (Post-Hardware Implementation):**
    *   Once `ReadRawADCValue` in `pkg/sensor/sensor.go` has real hardware logic:
        *   Simulate sensor failure if possible (e.g., disconnect the ADC or sensor).
        *   **Expected Outcome:** The sensor reading function should return an error. The main loop in `main.go` should log this error (e.g., "Error reading sensor value: ...") and skip the processing for that cycle, continuing to the next read attempt.

### Go Testing Tools

*   **`go test`:** Go's built-in testing tool is used to run test functions (those starting with `Test` in `_test.go` files).
    ```bash
    go test ./...  # Run tests in all packages
    go test ./pkg/config # Run tests for a specific package
    ```
*   **Table-Driven Tests:** A common pattern in Go for testing various inputs and outputs for a function.
*   **Assertion Libraries:** While Go's standard library doesn't include rich assertion functions, libraries like `github.com/stretchr/testify/assert` and `github.com/stretchr/testify/require` are widely used for more expressive tests.
*   **Mocking Libraries:** For dependencies like hardware or external services, `github.com/stretchr/testify/mock` can be used to create mock objects.

Remember to rebuild your Go application (`go build ...`) after any changes to the `.go` source files if you are testing the compiled binary. Using `go run ./cmd/cistern-monitor` is convenient for quick tests as it compiles and runs in one step.
