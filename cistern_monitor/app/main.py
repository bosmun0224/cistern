import time
from app.sensor import read_adc_value, convert_to_depth
from app.notifications import send_email
from app import config # Import the configuration module

def main_loop():
    """
    Main loop for the cistern monitoring application.
    Continuously reads sensor data, checks water levels, and sends notifications if needed.
    """
    print("--- Cistern Monitoring System Starting ---")
    print(f"Configuration (from app.config):")
    print(f"  ADC Channel: {config.ADC_CHANNEL}")
    print(f"  Tank Height: {config.TANK_HEIGHT_CM} cm")
    print(f"  ADC Max Value: {config.ADC_MAX_VALUE}")
    print(f"  Water Depth Alert Threshold: {config.WATER_DEPTH_THRESHOLD_CM} cm")
    print(f"  Read Interval: {config.READ_INTERVAL_SECONDS} seconds")
    print(f"  SMTP Server: {config.SMTP_SERVER}:{config.SMTP_PORT}")
    print(f"  Alert Recipient: {config.TO_EMAIL}")
    print("--- --- --- --- --- --- --- --- --- --- ---")
    print(f"WARNING: Ensure SMTP credentials in app.config are secure and correct for real alerts.")
    if config.SMTP_SERVER == "localhost" and config.SMTP_PORT == 1025:
        print("Hint: For testing with localhost:1025, run 'python -m smtpd -c DebuggingServer -n localhost:1025' in another terminal.")
    print("--- --- --- --- --- --- --- --- --- --- ---")

    while True:
        print(f"\n--- Starting new reading cycle at {time.strftime('%Y-%m-%d %H:%M:%S')} ---")
        try:
            # 1. Read sensor value
            print(f"Reading ADC value from channel {config.ADC_CHANNEL}...")
            adc_reading = read_adc_value(config.ADC_CHANNEL)
            print(f"Raw ADC reading: {adc_reading}")

            # 2. Convert to depth
            current_depth_cm = convert_to_depth(adc_reading, config.TANK_HEIGHT_CM, config.ADC_MAX_VALUE)
            print(f"Current simulated water depth: {current_depth_cm:.2f} cm")

            # 3. Check against threshold
            if current_depth_cm < config.WATER_DEPTH_THRESHOLD_CM:
                print(f"ALERT: Water level ({current_depth_cm:.2f} cm) is BELOW the threshold ({config.WATER_DEPTH_THRESHOLD_CM} cm).")

                subject = "Water Level Alert - Cistern Low"
                body = (f"Warning: Water level in the cistern is critically low.\n\n"
                        f"Current Depth: {current_depth_cm:.2f} cm\n"
                        f"Threshold: {config.WATER_DEPTH_THRESHOLD_CM} cm\n\n"
                        f"Time of reading: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"Please check the cistern and water supply.")

                print(f"Attempting to send email alert to {config.TO_EMAIL}...")
                email_sent = send_email(
                    subject=subject,
                    body=body,
                    to_email=config.TO_EMAIL,
                    smtp_server=config.SMTP_SERVER,
                    smtp_port=config.SMTP_PORT,
                    smtp_user=config.SMTP_USER,
                    smtp_password=config.SMTP_PASSWORD,
                    from_email=config.FROM_EMAIL
                )
                if email_sent:
                    print("Alert email sent successfully.")
                else:
                    print("Failed to send alert email. Check notification logs/settings.")
            else:
                print(f"Water level ({current_depth_cm:.2f} cm) is normal (above {config.WATER_DEPTH_THRESHOLD_CM} cm).")

        except Exception as e:
            print(f"ERROR during monitoring cycle: {e}")
            # Optionally, send a different kind of alert or log more detailed error
            # For now, we just print and continue the loop

        print(f"--- Cycle finished. Waiting for {config.READ_INTERVAL_SECONDS} seconds... ---")
        time.sleep(config.READ_INTERVAL_SECONDS)

if __name__ == '__main__':
    # Note: This will run an infinite loop. Press Ctrl+C to stop.
    # Ensure your placeholder configurations (especially for email) are set up
    # if you expect notifications to work (e.g., using a local SMTP debug server).
    main_loop()
