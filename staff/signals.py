from .models import *
from datetime import datetime,date,time
def create_employee_detail(sender, instance, created, **kwargs):
    if created:
        # Calculate the total leave
        current_year = date.today().year
        joined_year = instance.joined_date.year
        total_leave = max(13 - (current_year - joined_year), 0)

        # Create EmployeeDetail with calculated leave
        EmployeeDetail.objects.create(emp_register=instance, total_leave=total_leave)