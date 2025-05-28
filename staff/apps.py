from django.apps import AppConfig


class StaffConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff'



from django.apps import AppConfig

class StaffConfig(AppConfig): # The name 'StaffConfig' is common, can be slightly different
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'staff' # <-- This MUST be 'staff', matching INSTALLED_APPS

    def ready(self):
        """
        Import signals here to ensure they are connected when Django starts.
        """
        # --- This import is KEY for loading your signals ---
        import staff.signals # <-- This MUST be 'staff.signals'
        print("DEBUG: staff.signals loaded in apps.py ready()") # Temporary debug print
        # --------------------------------------------------