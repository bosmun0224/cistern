package config

// Config holds all application configuration parameters.
// Struct tags are included for potential future parsing from JSON/YAML files or environment variables.
type Config struct {
	// Sensor/ADC Configuration
	ADCDevice    string  `json:"adcDevice" yaml:"adcDevice"`         // Example: "/dev/spidev0.0" for SPI on Raspberry Pi
	ADCChannel   int     `json:"adcChannel" yaml:"adcChannel"`       // Example: 0 for channel CH0 on MCP3008
	TankHeightCM float64 `json:"tankHeightCM" yaml:"tankHeightCM"` // Total height of the water tank in cm
	ADCMaxValue  int     `json:"adcMaxValue" yaml:"adcMaxValue"`   // Max raw value from ADC (e.g., 1023 for 10-bit)

	// Alerting Configuration
	WaterDepthThresholdCM float64 `json:"waterDepthThresholdCM" yaml:"waterDepthThresholdCM"` // Alert if depth falls below this (cm)

	// Application Behavior
	ReadIntervalSeconds int `json:"readIntervalSeconds" yaml:"readIntervalSeconds"` // Time between sensor readings

	// SMTP Configuration for Email Notifications
	SMTPServer   string `json:"smtpServer" yaml:"smtpServer"`
	SMTPPort     int    `json:"smtpPort" yaml:"smtpPort"`
	SMTPUser     string `json:"smtpUser" yaml:"smtpUser"`
	SMTPPassword string `json:"smtpPassword" yaml:"smtpPassword"` // WARNING: Hardcoding passwords is very insecure. Use env vars or a secure vault in production.
	FromEmail    string `json:"fromEmail" yaml:"fromEmail"`       // Sender's email address
	ToEmail      string `json:"toEmail" yaml:"toEmail"`           // Recipient's email address
}

// LoadConfig provides a default configuration set.
// In a production application, this function would typically load settings from a configuration file
// (e.g., YAML, JSON, TOML) or environment variables, rather than hardcoding them.
func LoadConfig() Config {
	// Default values are provided here.
	// Users should ideally be able to override these through a config file or environment variables.
	return Config{
		// Sensor/ADC Configuration
		ADCDevice:    "/dev/spidev0.0", // Common for SPI-connected ADCs on Raspberry Pi. Adjust if needed.
		ADCChannel:   0,                // Default to channel 0.
		TankHeightCM: 200.0,            // Example: 2-meter high tank.
		ADCMaxValue:  1023,             // Default for a 10-bit ADC like MCP3008. Change for 12-bit (4095) etc.

		// Alerting Configuration
		WaterDepthThresholdCM: 50.0, // Alert if water is below 50 cm.

		// Application Behavior
		ReadIntervalSeconds: 300, // Check every 5 minutes (300 seconds).

		// SMTP Configuration - Defaults are set for a local SMTP debugging server.
		// For real email sending, these MUST be changed to actual SMTP provider details.
		SMTPServer: "localhost", // Use "smtp.gmail.com", "smtp.office365.com", etc. for real emails.
		SMTPPort:   1025,      // Common ports: 587 (TLS), 465 (SSL). 1025 for local debug server.
		SMTPUser:   "user@example.com", // Actual username for your SMTP server.
		// IMPORTANT: The password below is a placeholder and highly insecure if used as is.
		// For real use, obtain from environment variable or secure config management.
		SMTPPassword: "password",
		FromEmail:    "cistern-monitor@example.com", // Sender address.
		ToEmail:      "alerts-recipient@example.com",  // Who receives the alerts.
	}
}
