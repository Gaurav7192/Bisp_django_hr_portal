
import smtplib
import ssl
import certifi
# --- Email Configuration for gauravsinghbhandari77@gmail.com ---
# Gmail SMTP server details
smtp_server = "smtp.gmail.com"
port = 587  # Standard port for TLS

sender_email = "gauravsinghbhandari77@gmail.com"  # Your email address

# IMPORTANT:
# If you have 2-Step Verification enabled for gauravsinghbhandari77@gmail.com,
# this MUST be an "App password" generated from your Google Account security settings.
# It is NOT your regular Gmail password.
password = "rdzs lpza yels nhbl"  # <--- REPLACE THIS WITH YOUR APP PASSWORD!

# --- Optional: Recipient and Message for a full test email ---
# You can send it to your own email for testing purposes.
recipient_email = "gauravsinghbhandari77@gmail.com"
subject = "Test Email from Python Script (Django Troubleshooting)"
body = """
Hello Gaurav,

This is a test email sent from a Python script to verify SMTP connectivity
for your Django application's password reset functionality.

If you received this email, it means the Python script successfully connected
to the Gmail SMTP server and authenticated.

This helps confirm that:
1. Your internet connection allows outbound connections to smtp.gmail.com:587.
2. Your firewall is not blocking this connection.
3. The 'App Password' you used is correct.

If you are still facing ConnectionRefusedError in Django, please double-check
your Django settings.py for the EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS,
EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD values, ensuring they match these
working settings.

Best regards,
Your Python Test Script
"""
message = f"Subject: {subject}\n\n{body}"

print(f"Attempting to connect to {smtp_server}:{port} using {sender_email}...")

try:
    # Create a default SSL context for security.
    context = ssl.create_default_context()

    # Establish the SMTP connection for TLS (port 587)
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls(context=context)  # Secure the connection with TLS
        server.login(sender_email, password)  # Log in to the email account
        print("Login successful! Connection to Gmail SMTP server established.")

        # Send a test email (uncomment the next two lines to send)
        server.sendmail(sender_email, recipient_email, message)
        print(f"Test email sent successfully to {recipient_email}!")
        print("\nIf you received the email, your SMTP settings are likely correct.")
        print("Now, ensure your Django settings.py matches these values.")

except smtplib.SMTPAuthenticationError as e:
    print(f"ERROR: SMTP Authentication Failed!")
    print(f"Details: {e}")
    print(
        "This almost certainly means your 'App Password' is incorrect, or you're trying to use your regular Gmail password.")
    print("Please generate an App Password for your Google account and use it.")
except ConnectionRefusedError as e:
    print(f"ERROR: Connection Refused! This indicates a network or firewall issue.")
    print(f"Details: {e}")
    print("Possible reasons:")
    print("  - Your internet connection might be blocking the port 587.")
    print("  - Your local firewall (e.g., Windows Defender Firewall) is blocking outgoing connections.")
    print("  - The SMTP server address or port might be incorrect (less likely for Gmail standard).")
except smtplib.SMTPServerDisconnected as e:
    print(f"ERROR: SMTP Server Disconnected unexpectedly.")
    print(f"Details: {e}")
    print(
        "This can happen if the server dropped the connection, possibly due to invalid initial connection details or server issues.")
except smtplib.SMTPConnectError as e:
    print(f"ERROR: SMTP Connection Error. Could not establish a connection to the SMTP host.")
    print(f"Details: {e}")
    print("Likely a network issue preventing the initial connection.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")