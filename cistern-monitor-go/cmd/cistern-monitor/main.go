package main

import (
	"fmt"
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"example.com/cistern-monitor-go/pkg/config"
	"example.com/cistern-monitor-go/pkg/notifier"
	"example.com/cistern-monitor-go/pkg/sensor"
)

func main() {
	log.Println("INFO: Starting Cistern Water Level Monitor...")

	// Load configuration
	// In a real app, consider ways to gracefully handle config loading errors.
	cfg := config.LoadConfig()

	// Log some non-sensitive configuration details to confirm they are loaded.
	log.Printf("INFO: Configuration Loaded:")
	log.Printf("  Sensor - ADCDevice: %s, ADCChannel: %d, TankHeightCM: %.2f, ADCMaxValue: %d",
		cfg.ADCDevice, cfg.ADCChannel, cfg.TankHeightCM, cfg.ADCMaxValue)
	log.Printf("  Alerting - WaterDepthThresholdCM: %.2f", cfg.WaterDepthThresholdCM)
	log.Printf("  Timing - ReadIntervalSeconds: %d", cfg.ReadIntervalSeconds)
	log.Printf("  Email - SMTPServer: %s:%d, SMTPUser: %s, FromEmail: %s, ToEmail: %s",
		cfg.SMTPServer, cfg.SMTPPort, cfg.SMTPUser, cfg.FromEmail, cfg.ToEmail)
	// IMPORTANT: Avoid logging cfg.SMTPPassword directly.
	if cfg.SMTPPassword != "" && cfg.SMTPPassword != "password" { // Simple check if it's not the obvious default
		log.Println("  Email - SMTPPassword: [set]")
	} else if cfg.SMTPPassword == "password" {
		log.Println("  Email - SMTPPassword: [default placeholder used - ensure this is changed for production]")
	} else {
		log.Println("  Email - SMTPPassword: [not set]")
	}
	if cfg.SMTPServer == "localhost" && cfg.SMTPPort == 1025 {
		log.Println("HINT: Email is configured for a local debug server (e.g., 'python -m smtpd -c DebuggingServer -n localhost:1025')")
	}


	// Initialize Sensor
	// The sensor package currently uses placeholder logic for ReadRawADCValue().
	sensorReader := sensor.NewSensor(cfg.ADCChannel, cfg.ADCMaxValue, cfg.TankHeightCM)
	log.Println("INFO: Sensor component initialized (Note: ADC reading is currently a placeholder).")

	// Set up a channel to handle OS signals for graceful shutdown
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Main monitoring loop using a time.Ticker
	ticker := time.NewTicker(time.Duration(cfg.ReadIntervalSeconds) * time.Second)
	defer ticker.Stop() // Important to release ticker resources

	log.Println("INFO: Starting main monitoring loop. Press Ctrl+C to exit.")

	// Run the first check immediately without waiting for the first tick
	performMonitoringCycle(&cfg, sensorReader)

	for {
		select {
		case t := <-ticker.C:
			log.Printf("INFO: Monitoring cycle triggered by ticker at %v", t.Format(time.RFC3339))
			performMonitoringCycle(&cfg, sensorReader)
		case s := <-sigChan:
			log.Printf("INFO: Received signal: %v. Shutting down gracefully...", s)
			// Perform any cleanup here if necessary
			log.Println("INFO: Cistern Water Level Monitor stopped.")
			return
		}
	}
}

// performMonitoringCycle contains the logic for a single sensor reading and alerting cycle.
func performMonitoringCycle(cfg *config.Config, sensorReader *sensor.Sensor) {
	log.Println("INFO: --- New Monitoring Cycle ---")
	defer log.Println("INFO: --- Monitoring Cycle Finished ---")

	rawValue, err := sensorReader.ReadRawADCValue()
	if err != nil {
		// In a real scenario, this error would come from actual hardware interaction.
		log.Printf("ERROR: Failed to read sensor value: %v. Skipping this cycle.\n", err)
		return // Skip to the next tick
	}

	currentDepthCM := sensorReader.ConvertToDepth(rawValue)
	log.Printf("DATA: Raw ADC Value: %d, Calculated Depth: %.2f cm\n", rawValue, currentDepthCM)

	if currentDepthCM < cfg.WaterDepthThresholdCM {
		alertMsg := fmt.Sprintf("ALERT: Water level (%.2f cm) is BELOW the configured threshold (%.2f cm)!", currentDepthCM, cfg.WaterDepthThresholdCM)
		log.Println(alertMsg)

		subject := "Cistern Water Level Alert - LOW"
		body := fmt.Sprintf(
			"Water Level Alert:\n\n"+
				"The water level in the cistern is currently measured at %.2f cm.\n"+
				"This is below the configured threshold of %.2f cm.\n\n"+
				"Details:\n"+
				"  - Time of Reading: %s\n"+
				"  - Raw ADC Value: %d\n"+
				"  - Configured Tank Height: %.2f cm\n"+
				"  - Configured ADC Max Value: %d\n\n"+
				"Please check the cistern and water supply.",
			currentDepthCM,
			cfg.WaterDepthThresholdCM,
			time.Now().Format(time.RFC1123Z),
			rawValue,
			cfg.TankHeightCM,
			cfg.ADCMaxValue,
		)

		// Prepare email configuration for the notifier
		emailNotifierCfg := notifier.EmailConfig{
			SMTPServer:   cfg.SMTPServer,
			SMTPPort:     cfg.SMTPPort,
			SMTPUser:     cfg.SMTPUser,
			SMTPPassword: cfg.SMTPPassword, // Pass with caution, ensure it's handled securely in notifier or by environment
			FromEmail:    cfg.FromEmail,
		}

		// Attempt to send the email
		// Using the basic SendEmail function. For Gmail/O365, SendEmailWithExplicitTLS might be needed.
		log.Printf("INFO: Attempting to send alert email to %s...\n", cfg.ToEmail)
		sendErr := notifier.SendEmail(emailNotifierCfg, cfg.ToEmail, subject, body)
		if sendErr != nil {
			log.Printf("ERROR: Failed to send alert email: %v\n", sendErr)
		} else {
			log.Println("INFO: Alert email sent successfully.")
		}
	} else {
		log.Printf("INFO: Water level (%.2f cm) is normal (Threshold: %.2f cm).\n", currentDepthCM, cfg.WaterDepthThresholdCM)
	}
}
