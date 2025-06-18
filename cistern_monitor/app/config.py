# Cistern Monitoring System Configuration
# ---------------------------------------
# Users should update these values according to their specific hardware setup,
# preferences, and email server details.

# --- Sensor Configuration ---
ADC_CHANNEL = 0  # ADC channel connected to the water level sensor (e.g., 0 for MCP3008 channel CH0)
TANK_HEIGHT_CM = 200.0  # Full height of the water tank in centimeters. Used for converting ADC reading to depth.
ADC_MAX_VALUE = 1023  # Maximum raw value from your ADC (e.g., 1023 for a 10-bit ADC like MCP3008, 4095 for 12-bit).

# --- Alerting Configuration ---
WATER_DEPTH_THRESHOLD_CM = 50.0  # Send an alert if the water depth falls below this value (in cm).

# --- Application Timing ---
# Interval in seconds between sensor readings and checks.
READ_INTERVAL_SECONDS = 300  # (e.g., 300 seconds = 5 minutes, 3600 = 1 hour)

# --- Email Notification Configuration ---
# IMPORTANT: For sensitive information like passwords, it's highly recommended to use
# environment variables, a secrets management tool, or a more secure config loading approach
# in a production environment instead of hardcoding them in this file.

SMTP_SERVER = "localhost"  # SMTP server address (e.g., "smtp.gmail.com")
                            # For testing with a local debug server: "localhost"
SMTP_PORT = 1025           # SMTP server port (e.g., 587 for TLS, 465 for SSL)
                            # For testing with a local debug server: 1025

SMTP_USER = "your_email@example.com"  # Username for SMTP authentication
                                      # For local debug server, this might not be strictly needed.

# !!! WARNING: Storing passwords in plaintext is insecure. !!!
# Consider using environment variables or a secure vault for production.
# Example: SMTP_PASSWORD = os.environ.get('SMTP_PASS')
SMTP_PASSWORD = "your_password"       # Password for SMTP authentication.
                                      # For local debug server, this might not be strictly needed.

FROM_EMAIL = "cistern.alerts@example.com"  # Email address to send notifications from.
                                          # Some SMTP servers may require this to be the same as SMTP_USER.

TO_EMAIL = "user_to_notify@example.com"    # Email address to send notifications to.
                                          # Can be a single address or a comma-separated list if your
                                          # send_email function is adapted to handle it.

# --- Other Potential Configurations (Examples - not used by current main.py directly) ---
# LOG_FILE_PATH = "/var/log/cistern_monitor.log"
# DEBUG_MODE = False
# SENSOR_TYPE = "HC-SR04" # Could be 'MCP3008_POTENTIOMETER' or 'ULTRASONIC_HCSR04' etc.
# CALIBRATION_FACTOR = 1.0 # For fine-tuning sensor readings
