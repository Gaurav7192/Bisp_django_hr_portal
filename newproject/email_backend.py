
import ssl
from django.core.mail.backends.smtp import EmailBackend

class NoSSLContextEmailBackend(EmailBackend):
    def _get_ssl_context(self):
        context = ssl._create_default_https_context()  # Default context without verification
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context