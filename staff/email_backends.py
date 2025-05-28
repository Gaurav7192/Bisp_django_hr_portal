import ssl
from django.core.mail.backends.smtp import EmailBackend

class BypassSSLVerificationEmailBackend(EmailBackend):
    """
    A custom email backend that bypasses SSL certificate verification.
    USE ONLY FOR DEVELOPMENT. DO NOT USE IN PRODUCTION.
    """
    def _get_connection(self):
        # Override the _get_connection method to use an unverified SSL context
        if self.use_tls:
            # For STARTTLS, we create a regular SMTP connection and then start TLS with unverified context
            self.connection = self.connection_class(self.host, self.port, timeout=self.timeout)
            self.connection.starttls(context=ssl._create_unverified_context())
        elif self.use_ssl:
            # For SMTPS (SSL directly), we use SMTP_SSL with unverified context
            self.connection = self.connection_class(
                self.host, self.port, timeout=self.timeout,
                context=ssl._create_unverified_context()
            )
        else:
            # Fallback for non-TLS/SSL connections (not recommended for email)
            self.connection = self.connection_class(self.host, self.port, timeout=self.timeout)

        return self.connection
