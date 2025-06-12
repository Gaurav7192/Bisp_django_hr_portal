from django.contrib import admin

# Register your models here.
# staff/admin.py
from django.contrib import admin
from .models import HRPolicy

@admin.register(HRPolicy)
class HRPolicyAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at')
    search_fields = ('title', 'content')