import smtplib
from email.mime.text import MIMEText

def send_email(subject: str, body: str, to_email: str,
               smtp_server: str, smtp_port: int,
               smtp_user: str, smtp_password: str,
               from_email: str = None):
    """
    Sends an email using the specified SMTP server and credentials.

    Args:
        subject: The subject line of the email.
        body: The main content/body of the email.
        to_email: The recipient's email address.
        smtp_server: The SMTP server address (e.g., 'smtp.gmail.com').
        smtp_port: The SMTP server port (e.g., 587 for TLS, 465 for SSL).
        smtp_user: The username for SMTP authentication.
        smtp_password: The password for SMTP authentication.
        from_email: (Optional) The sender's email address. If None, smtp_user is used.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    if not from_email:
        from_email = smtp_user

    msg = MIMEText(body, 'plain')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        # Using SMTP_SSL for implicit SSL, or SMTP with starttls() for explicit TLS
        # Gmail and many others use port 465 for SMTP_SSL or 587 for SMTP + starttls
        if smtp_port == 465: # Common SSL port
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        else: # Common TLS port (587) or other non-SSL and then upgrade
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo() # Extended HELO for server capabilities
            server.starttls() # Secure the connection
            server.ehlo() # Re-send ehlo after starting TLS

        print(f"Attempting to log in to SMTP server {smtp_server}:{smtp_port} as {smtp_user}...")
        server.login(smtp_user, smtp_password)
        print("Logged in successfully.")

        print(f"Sending email to {to_email} from {from_email} with subject '{subject}'...")
        server.sendmail(from_email, to_email, msg.as_string())
        print("Email sent successfully.")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}. Check username/password and mail server settings (e.g., 'less secure app access' for Gmail).")
        return False
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP Server Disconnected: {e}. Check server address, port, or network.")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"SMTP Connect Error: {e}. Check server address and port.")
        return False
    except smtplib.SMTPException as e:
        print(f"An SMTP error occurred: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False
    finally:
        if 'server' in locals() and server:
            try:
                server.quit()
                print("SMTP server connection closed.")
            except smtplib.SMTPServerDisconnected:
                # Server might have already disconnected if there was an issue
                print("SMTP server already disconnected.")


if __name__ == '__main__':
    print("Running notification module test...")
    # --- IMPORTANT ---
    # The following are PLACEHOLDER credentials and server details.
    # DO NOT commit real credentials to version control.
    # Replace these with your actual email server details and credentials for testing.
    # For Gmail, you might need to enable "Less secure app access" or use an "App Password".
    # --- --- --- ---
    TEST_SUBJECT = "Cistern Monitor Test Email"
    TEST_BODY = "This is a test email from the Cistern Monitoring System."
    TEST_TO_EMAIL = "recipient@example.com"  # Replace with a real recipient for testing

    # --- PLACEHOLDER SMTP DETAILS ---
    # Option 1: Gmail (requires "App Password" if 2FA is enabled, or "Less Secure App Access")
    # SMTP_SERVER_ADDRESS = "smtp.gmail.com"
    # SMTP_SERVER_PORT = 587 # For TLS
    # SMTP_USERNAME = "your_email@gmail.com"
    # SMTP_APP_PASSWORD = "your_gmail_app_password" # Replace with your App Password

    # Option 2: Other email provider (e.g., Outlook, Yahoo, custom)
    # Check your provider's documentation for SMTP server, port, and security (SSL/TLS)
    # SMTP_SERVER_ADDRESS = "smtp.office365.com" # Example for Outlook
    # SMTP_SERVER_PORT = 587 # For TLS
    # SMTP_USERNAME = "your_email@outlook.com"
    # SMTP_APP_PASSWORD = "your_password"

    # Option 3: Use a local SMTP debug server (for development without sending real emails)
    # Run `python -m smtpd -c DebuggingServer -n localhost:1025` in a separate terminal
    # Then use the following:
    SMTP_SERVER_ADDRESS = "localhost"
    SMTP_SERVER_PORT = 1025
    SMTP_USERNAME = "user" # Not usually used by DebuggingServer
    SMTP_APP_PASSWORD = "password" # Not usually used by DebuggingServer
    # --- --- --- ---

    print(f"\n--- Attempting to send a test email using LOCAL DEBUG SMTP SERVER (localhost:1025) ---")
    print(f"Ensure you have a local SMTP debug server running on localhost:1025 for this to work.")
    print(f"Example: python -m smtpd -c DebuggingServer -n localhost:1025")

    success = send_email(
        subject=TEST_SUBJECT,
        body=TEST_BODY,
        to_email=TEST_TO_EMAIL,
        smtp_server=SMTP_SERVER_ADDRESS,
        smtp_port=SMTP_SERVER_PORT,
        smtp_user=SMTP_USERNAME, # For local debug server, often not needed
        smtp_password=SMTP_APP_PASSWORD # For local debug server, often not needed
    )

    if success:
        print(f"\nTest email function executed. If using a real SMTP server, check {TEST_TO_EMAIL}.")
        print("If using the local debug server, check its console output for the email.")
    else:
        print(f"\nTest email function failed. See error messages above.")

    print("\n--- If you want to test with a REAL email provider: ---")
    print("1. Uncomment and fill in the SMTP details for your provider in the __main__ block.")
    print("2. Ensure your email account allows SMTP access (e.g., 'less secure app access' or 'app passwords' for Gmail).")
    print("3. Replace TEST_TO_EMAIL with a valid recipient email address.")
    print("4. Run the script again: python cistern_monitor/app/notifications.py")
    print("--- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- --- ---")
