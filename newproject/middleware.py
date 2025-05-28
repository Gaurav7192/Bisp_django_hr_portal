class DisableCacheMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
import os
import datetime
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from django.utils.timezone import now

class UserAuditLogMiddleware(MiddlewareMixin):
    """
    Middleware to log user activity to a daily audit log file.
    """

    def process_request(self, request):
        # Only log if the user is authenticated
        if request.user.is_authenticated:
            # Prepare the log directory
            log_dir = os.path.join(settings.BASE_DIR, 'audit_logs')
            os.makedirs(log_dir, exist_ok=True)

            # Use IST timezone offset in case using naive datetime, adjust if needed.
            # Here using server local timezone or you may customize as desired.
            date_str = now().strftime('%Y-%m-%d')
            log_file_path = os.path.join(log_dir, f'{request.user.username}_{date_str}.log')

            # Compose the log message
            time_str = now().strftime('%Y-%m-%d %H:%M:%S')
            method = request.method
            path = request.get_full_path()
            ip = self.get_client_ip(request)

            log_line = f"{time_str} | {ip} | {method} {path}\n"

            # Append the log line to the user's daily file
            with open(log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_line)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

