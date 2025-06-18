package notifier

import (
	"crypto/tls"
	"fmt"
	"log"
	"net/smtp"
	"strings"
)

// EmailConfig holds the necessary configuration details for sending an email.
type EmailConfig struct {
	SMTPServer   string // SMTP server address (e.g., "smtp.gmail.com")
	SMTPPort     int    // SMTP server port (e.g., 587 for TLS, 465 for SSL, 1025 for local debug)
	SMTPUser     string // Username for SMTP authentication
	SMTPPassword string // Password for SMTP authentication (handle with care)
	FromEmail    string // Sender's email address
}

// SendEmail sends a plain text email.
// This function uses the standard net/smtp.SendMail, which has limitations:
// - It attempts opportunistic STARTTLS if the server advertises it after an initial unencrypted connection.
// - It does not handle direct SSL/TLS connections (typically on port 465) explicitly.
// For robust sending to servers like Gmail or Office365 (which often use port 587/STARTTLS or 465/SSL),
// a more detailed implementation like SendEmailWithExplicitTLS (see below) is often required.
// This basic version is generally fine for local SMTP debug servers (e.g., on localhost:1025).
func SendEmail(config EmailConfig, toEmail, subject, bodyMessage string) error {
	serverAddr := fmt.Sprintf("%s:%d", config.SMTPServer, config.SMTPPort)

	// Construct the email message with basic headers.
	var msgBuilder strings.Builder
	msgBuilder.WriteString(fmt.Sprintf("From: %s\r\n", config.FromEmail)) // Use CRLF line endings
	msgBuilder.WriteString(fmt.Sprintf("To: %s\r\n", toEmail))
	msgBuilder.WriteString(fmt.Sprintf("Subject: %s\r\n", subject))
	// Standard says "MIME-Version" but "MIME-version" is common.
	// Using text/plain; charset="UTF-8" for broad compatibility.
	msgBuilder.WriteString("MIME-Version: 1.0\r\n")
	msgBuilder.WriteString("Content-Type: text/plain; charset=\"UTF-8\"\r\n")
	msgBuilder.WriteString("\r\n") // Empty line separates headers from the body
	msgBuilder.WriteString(bodyMessage + "\r\n")

	msg := []byte(msgBuilder.String())

	var auth smtp.Auth
	// smtp.PlainAuth will only send credentials if the server advertises auth after connecting,
	// and typically only over a secure connection (TLS) unless it's localhost.
	if config.SMTPUser != "" && config.SMTPPassword != "" {
		// Note: PlainAuth is not secure over unencrypted connections unless it's localhost.
		// smtp.SendMail will attempt STARTTLS if available.
		auth = smtp.PlainAuth("", config.SMTPUser, config.SMTPPassword, config.SMTPServer)
	}

	log.Printf("INFO: Attempting to send email to %s via %s using basic smtp.SendMail\n", toEmail, serverAddr)

	err := smtp.SendMail(serverAddr, auth, config.FromEmail, []string{toEmail}, msg)
	if err != nil {
		log.Printf("ERROR: Failed to send email using smtp.SendMail: %v\n", err)
		// Provide more context for common issues.
		if strings.Contains(err.Error(), "authentication required") || strings.Contains(err.Error(), "Username and Password not accepted") {
			log.Println("HINT: Check SMTP username/password. For Gmail/GSuite, an 'App Password' may be required if 2FA is enabled.")
			log.Println("HINT: Also, ensure your mail server allows 'less secure apps' or that PlainAuth is appropriate for its security policy.")
		}
		if strings.Contains(err.Error(), "connection refused") {
			log.Printf("HINT: Connection to %s was refused. Is the SMTP server address and port correct and reachable?\n", serverAddr)
		}
		return fmt.Errorf("smtp.SendMail failed: %w", err)
	}

	log.Printf("INFO: Email successfully sent to %s via %s (using basic smtp.SendMail)\n", toEmail, serverAddr)
	return nil
}

// SendEmailWithExplicitTLS provides a more robust way to send emails, especially for servers
// requiring STARTTLS (like Gmail on port 587) or direct TLS (port 465).
// This function is provided for reference and more complex scenarios.
func SendEmailWithExplicitTLS(config EmailConfig, toEmail, subject, bodyMessage string) error {
	serverAddr := fmt.Sprintf("%s:%d", config.SMTPServer, config.SMTPPort)

	// Construct the email message (same as above)
	var msgBuilder strings.Builder
	msgBuilder.WriteString(fmt.Sprintf("From: %s\r\n", config.FromEmail))
	msgBuilder.WriteString(fmt.Sprintf("To: %s\r\n", toEmail))
	msgBuilder.WriteString(fmt.Sprintf("Subject: %s\r\n", subject))
	msgBuilder.WriteString("MIME-Version: 1.0\r\n")
	msgBuilder.WriteString("Content-Type: text/plain; charset=\"UTF-8\"\r\n")
	msgBuilder.WriteString("\r\n")
	msgBuilder.WriteString(bodyMessage + "\r\n")
	msgContent := []byte(msgBuilder.String())

	auth := smtp.PlainAuth("", config.SMTPUser, config.SMTPPassword, config.SMTPServer)

	log.Printf("INFO: Attempting to send email to %s via %s using explicit TLS logic\n", toEmail, serverAddr)

	// For port 465 (SMTPS - SMTP over direct SSL/TLS)
	if config.SMTPPort == 465 {
		tlsconfig := &tls.Config{
			ServerName: config.SMTPServer,
		}
		conn, err := tls.Dial("tcp", serverAddr, tlsconfig)
		if err != nil {
			return fmt.Errorf("failed to dial TLS for port 465: %w", err)
		}
		client, err := smtp.NewClient(conn, config.SMTPServer)
		if err != nil {
			return fmt.Errorf("failed to create SMTP client over TLS: %w", err)
		}
		defer client.Close()

		if auth != nil {
			if err = client.Auth(auth); err != nil {
				return fmt.Errorf("SMTP authentication failed over TLS (465): %w", err)
			}
		}
		// Proceed with Mail, Rcpt, Data sequence
		if err = client.Mail(config.FromEmail); err != nil {
			return fmt.Errorf("failed to set sender (TLS 465): %w", err)
		}
		if err = client.Rcpt(toEmail); err != nil {
			return fmt.Errorf("failed to set recipient (TLS 465): %w", err)
		}
		w, err := client.Data()
		if err != nil {
			return fmt.Errorf("failed to get data writer (TLS 465): %w", err)
		}
		_, err = w.Write(msgContent)
		if err != nil {
			return fmt.Errorf("failed to write message data (TLS 465): %w", err)
		}
		err = w.Close()
		if err != nil {
			return fmt.Errorf("failed to close data writer (TLS 465): %w", err)
		}
		log.Printf("INFO: Email successfully sent to %s via %s (SMTPS/465)\n", toEmail, serverAddr)
		return client.Quit()
	}

	// For port 587 (STARTTLS) or other ports where STARTTLS might be used
	client, err := smtp.Dial(serverAddr) // Initial unencrypted connection
	if err != nil {
		return fmt.Errorf("failed to dial SMTP server: %w", err)
	}
	defer client.Close()

	// Check for STARTTLS support and upgrade if available
	if ok, _ := client.Extension("STARTTLS"); ok {
		tlsConfig := &tls.Config{
			ServerName: config.SMTPServer,
			// InsecureSkipVerify: true, // DO NOT USE IN PRODUCTION unless absolutely necessary and understood
		}
		if err = client.StartTLS(tlsConfig); err != nil {
			return fmt.Errorf("failed to start TLS: %w", err)
		}
	} else {
		// If STARTTLS is not supported but we are not on localhost, it's a concern for security
		// unless it's an explicit non-TLS internal relay.
		// For localhost (like a debug server), unencrypted is often fine.
		if config.SMTPServer != "localhost" && config.SMTPServer != "127.0.0.1" {
			log.Println("WARNING: STARTTLS not supported by server. Authentication, if used, will be sent over unencrypted connection.")
		}
	}

	// Authenticate if credentials provided and server supports AUTH after potential STARTTLS
	if auth != nil {
		if ok, _ := client.Extension("AUTH"); ok { // Check if AUTH is advertised
			if err = client.Auth(auth); err != nil {
				return fmt.Errorf("SMTP authentication failed: %w", err)
			}
		} else {
			log.Println("INFO: AUTH not supported by server (after STARTTLS if any). Skipping auth.")
		}
	}

	// Send mail sequence
	if err = client.Mail(config.FromEmail); err != nil {
		return fmt.Errorf("failed to set sender: %w", err)
	}
	if err = client.Rcpt(toEmail); err != nil {
		return fmt.Errorf("failed to set recipient: %w", err)
	}
	w, err := client.Data()
	if err != nil {
		return fmt.Errorf("failed to get data writer: %w", err)
	}
	_, err = w.Write(msgContent)
	if err != nil {
		return fmt.Errorf("failed to write message data: %w", err)
	}
	err = w.Close()
	if err != nil {
		return fmt.Errorf("failed to close data writer: %w", err)
	}

	log.Printf("INFO: Email successfully sent to %s via %s (using STARTTLS if available)\n", toEmail, serverAddr)
	return client.Quit()
}
