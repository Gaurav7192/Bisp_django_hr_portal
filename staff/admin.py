from django.contrib import admin

# Register your models here.
# staff/admin.py
from django.contrib import admin
from .models import HRPolicy

@admin.register(HRPolicy)
class HRPolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
# profiles/admin.py

from django.contrib import admin
from .models import * # Import EmpRegister

# Register your models here so they appear in the Django admin interface
admin.site.register(UserProfile)
admin.site.register(emp_registers) # Register the new model