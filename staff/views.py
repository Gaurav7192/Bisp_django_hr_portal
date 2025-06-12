from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from datetime import datetime,date

from django.shortcuts import get_object_or_404
import re
from django.utils.dateparse import parse_date
from django.contrib.auth.hashers import make_password
from django import forms
from django.contrib.auth.hashers import check_password
from datetime import timedelta
import time
from django.contrib.auth import authenticate, login
from .form import *
from django.utils.timezone import now
from django.http import JsonResponse
from decimal import Decimal
import random
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from .form import *
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import LeaveTypeMaster, LeaveRecord
import json
from django.db import transaction
from .utils.audit import log_user_action

def d1(request,id):
    user = get_object_or_404(emp_registers, id=id)

    return render(request, '1.html', {'user': user})

def d2(request,id):
    user = get_object_or_404(emp_registers, id=id)

    return render(request, '2.html', {'user': user})





from django.contrib.auth.decorators import login_required
from django.db.models import Q

from .models import (
    emp_registers, EmployeeDetail, LeaveRecord, LeaveStatusMaster, Holiday,
    Project, Resignation, Handbook, Acknowledgment, RoleMaster, ResignationStatusMaster # Ensure all models are imported
)
from .audit_logger import log_audit_action

# Helper function to get the user identifier from session
def get_user_audit_identifier(request):
    # Prioritize request.session.name if set, otherwise use request.user.name as fallback
    # If neither, fall back to a generic 'Unknown'
    return request.session.get('name', request.user.name if request.user.is_authenticated else 'Unknown/Anonymous')



def dashboard_view(request):
    user = request.user
    user_audit_name = get_user_audit_identifier(request) # Get name from session

    employee_detail = None
    user_total_holidays = 0
    is_hr = False
    pending_leaves = []
    recent_projects = []
    ending_projects = []
    pending_resignations = []
    show_handbook_notice = False

    # ... (rest of your dashboard_view logic) ...

    try:
        employee_detail = EmployeeDetail.objects.get(emp_id=user)
    except EmployeeDetail.DoesNotExist:
        employee_detail = None
        log_audit_action(user_audit_name, "attempted to view dashboard but EmployeeDetail missing")


    user_total_holidays = Holiday.objects.count()

    hr_role = RoleMaster.objects.filter(role='HR').first()
    if hr_role and user.position == hr_role:
        is_hr = True

        pending_status = get_object_or_404(LeaveStatusMaster, status='Pending')
        pending_leaves = LeaveRecord.objects.filter(approval_status=pending_status).select_related('emp_id', 'leave_type')

        today = date.today()
        three_days_ago = today - timedelta(days=3)
        three_days_later = today + timedelta(days=3)

        recent_projects = Project.objects.filter(start_date__gte=three_days_ago, start_date__lte=today).order_by('-start_date')

        ending_projects = Project.objects.filter(
            Q(end_date__gte=today) & Q(end_date__lte=three_days_later)
        ).exclude(status__status='Completed').order_by('end_date')

        pending_resignation_status = ResignationStatusMaster.objects.filter(
            status_name__in=['Submitted', 'Pending']
        ).first()

        if pending_resignation_status:
            pending_resignations = Resignation.objects.filter(
                resign_status=pending_resignation_status
            ).select_related('employee')

    if not request.session.get('handbook_notice_shown', False):
        active_handbooks = Handbook.objects.filter(
            active_status=True,
            start_date__lte=date.today()
        ).exclude(end_date__lt=date.today())
        latest_active_handbook = active_handbooks.order_by('-start_date').first()

        if latest_active_handbook:
            acknowledged = Acknowledgment.objects.filter(
                employee=user,
                handbook=latest_active_handbook,
                acknowledgment='agree'
            ).exists()

            if not acknowledged:
                show_handbook_notice = True
                request.session['handbook_notice_shown'] = True
                log_audit_action(user_audit_name, f"Handbook acknowledgment notice displayed for '{latest_active_handbook.document_name}'")


    context = {
        'user': user,
        'employee_detail': employee_detail,
        'user_total_holidays': user_total_holidays,
        'is_hr': is_hr,
        'pending_leaves': pending_leaves,
        'recent_projects': recent_projects,
        'ending_projects': ending_projects,
        'pending_resignations': pending_resignations,
        'show_handbook_notice': show_handbook_notice,
        'latest_active_handbook': latest_active_handbook if show_handbook_notice else None,
    }

    log_audit_action(user_audit_name, "viewed dashboard") # Use the session name here
    return render(request, 'staff/dashboard.html', context)



def resignation_detail_view(request, pk):
    user_audit_name = get_user_audit_identifier(request) # Get name from session
    resignation = get_object_or_404(Resignation, pk=pk)
    # Add security
    if not request.user.is_superuser and not (request.user.position and request.user.position.role == 'HR') and resignation.employee != request.user:
        log_audit_action(user_audit_name, f"attempted unauthorized access to resignation details for {resignation.employee.name} (ID: {pk})")
        return redirect('dashboard')

    context = {
        'resignation': resignation
    }
    log_audit_action(user_audit_name, f"viewed resignation details for {resignation.employee.name} (ID: {pk})")
    return render(request, 'staff/resignation_detail.html', context)

def approve_leave_view(request, pk):
    user_audit_name = get_user_audit_identifier(request) # Get name from session
    if not (request.user.position and request.user.position.role == 'HR'):
        log_audit_action(user_audit_name, f"attempted unauthorized leave approval for ID: {pk}")
        return redirect('dashboard')

    leave_record = get_object_or_404(LeaveRecord, pk=pk)
    if request.method == 'POST':
        approved_status = get_object_or_404(LeaveStatusMaster, status='Approved')
        leave_record.approval_status = approved_status
        leave_record.approved_by = request.user.name # Or request.user.email
        leave_record.save()
        log_audit_action(user_audit_name, f"approved leave request (ID: {pk}) for {leave_record.emp_id.name}")
        return redirect('dashboard')
    context = {'leave_record': leave_record}
    return render(request, 'staff/confirm_leave_action.html', context)

@login_required
def reject_leave_view(request, pk):
    user_audit_name = get_user_audit_identifier(request) # Get name from session
    if not (request.user.position and request.user.position.role == 'HR'):
        log_audit_action(user_audit_name, f"attempted unauthorized leave rejection for ID: {pk}")
        return redirect('dashboard')

    leave_record = get_object_or_404(LeaveRecord, pk=pk)
    if request.method == 'POST':
        rejected_status = get_object_or_404(LeaveStatusMaster, status='Rejected')
        leave_record.approval_status = rejected_status
        leave_record.approved_by = request.user.name # Or request.user.email
        leave_record.save()
        log_audit_action(user_audit_name, f"rejected leave request (ID: {pk}) for {leave_record.emp_id.name}")
        return redirect('dashboard')
    context = {'leave_record': leave_record}
    return render(request, 'staff/confirm_leave_action.html', context)

# Add other views here where you call log_audit_action
# Example:

def update_profile_view(request):
    user_audit_name = get_user_audit_identifier(request)
    employee_instance = get_object_or_404(emp_registers, pk=request.user.pk)
    if request.method == 'POST':
        # ... process form data and save employee_instance ...
        employee_instance.save()
        log_audit_action(user_audit_name, "updated own profile details")
        return redirect('profile_view')
    return render(request, 'profile_form.html', {'employee_instance': employee_instance})

def view_all_projects(request):
    print(f"*** VIEW FUNCTION CALLED: view_all_projects for {request.user.username} ***") # <-- ADD THIS
    projects = Project.objects.all()
    log_audit_action(request.user.username, "opened all projects list")
    return render(request, 'projects/project_list.html', {'projects': projects})
def home_view(request):
    return render(request, 'home.html')

# newproject/staff/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

# --- Import from the same app's audit_logger.py ---
from .audit_logger import log_audit_action
# -------------------------------------------------

from .models import Project, emp_registers, LeaveRecord # Your models used in views

def view_all_projects(request):
    print(f"DEBUG: 'view_all_projects' view function called by {request.user.username}") # More debug
    projects = Project.objects.all()
    log_audit_action(request.user.username, "opened all projects list")
    return render(request, 'projects/project_list.html', {'projects': projects})


def approve_leave_view(request, leave_id):
    leave_record = get_object_or_404(LeaveRecord, pk=leave_id)
    if request.method == 'POST':
        # ... logic to approve the leave ...
        # Make sure your LeaveRecord save logic is correct and updates the instance
        # Example:
        # leave_record.approval_status = LeaveStatusMaster.objects.get(status='Approved')
        # leave_record.approved_by = request.user.emp_registers.name # Adjust based on how you link Auth.User to emp_registers
        leave_record.save() # This save triggers the post_save signal for LeaveRecord

        log_audit_action(request.user.username,
                         f"approved leave application (ID: {leave_id}) for {leave_record.emp_id.name}")
        return redirect('leave_list')
    return render(request, 'approve_leave_form.html', {'leave_record': leave_record})

# Add log_audit_action calls to any other views where specific user actions occur
# Example: Employee updating their profile (if not via a model signal)

def update_profile_view(request):
    employee_detail = get_object_or_404(emp_registers, pk=request.user.pk) # Adjust based on your user model
    if request.method == 'POST':
        # ... process form data and save employee_detail ...
        employee_detail.save() # This save will trigger the post_save for emp_registers
        log_audit_action(request.user.username, "updated own profile details")
        return redirect('profile_view')
    return render(request, 'profile_form.html', {'employee_detail': employee_detail})


from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime
import re

from .models import emp_registers

def update_employee(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    employee = get_object_or_404(emp_registers, id=id)

    if request.method == 'POST':
        form = EmployeeForm(request.POST, instance=employee)
        if form.is_valid():
            cleaned_data = form.cleaned_data
            name = cleaned_data.get('name')
            email = cleaned_data.get('email')
            password = cleaned_data.get('password')
            position = cleaned_data.get('position')
            department = cleaned_data.get('department')
            joindate = cleaned_data.get('joindate')
            reportto = cleaned_data.get('reportto')

            # 1. Check required fields manually
            if not all([name, email, position, department, joindate, reportto]):
                messages.error(request, 'All fields are required!', extra_tags="update_emp")
                return redirect('update_employee', id=id)

            # 2. Validate Password (if entered)
            if password:
                if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*]', password):
                    messages.error(request, 'Password must be at least 8 characters, include an uppercase letter, a number, and a special character.', extra_tags="update_emp")
                    return redirect('update_employee', id=id)

            # 3. Check join date logic
            try:
                if joindate > datetime.today().date():
                    messages.error(request, 'Joining date cannot be in the future.', extra_tags="update_emp")
                    return redirect('update_employee', id=id)

                if joindate < datetime(2025, 1, 1).date():
                    messages.error(request, 'Joining date cannot be before January 1, 2025.', extra_tags="update_emp")
                    return redirect('update_employee', id=id)
            except ValueError:
                messages.error(request, 'Invalid join date format.', extra_tags="update_emp")
                return redirect('update_employee', id=id)

            # 4. Save the form data
            form.save()
            messages.success(request, "Employee details updated successfully!", extra_tags="update_emp")
            return redirect('employee_list')

        else:
            messages.error(request, "Failed to update. Please correct the errors in the form.", extra_tags="update_emp")

    else:
        form = EmployeeForm(instance=employee)

    return render(request, 'update_employee.html', {'form': form, 'employee': employee})



# staff/views.py (or wherever your login view is located)

from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings  # To access LOGIN_ATTEMPT_THRESHOLD and LOCKOUT_DURATION_HOURS
from django.utils import timezone  # For time-based lockout calculations
from .models import emp_registers  # Your custom user model (emp_registers)
from django.contrib.auth.hashers import check_password # <<< IMPORTANT: Ensure this import is present!

# Make sure emp_registers model has:
# - failed_login_attempts (IntegerField, default=0)
# - account_locked_until (DateTimeField, null=True, blank=True)
# - is_locked() method
# - lock_account(duration_hours=2) method
# - unlock_account() method
# And that you've run migrations after adding these fields/methods.
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import check_password # Make sure this is imported

# Assuming emp_registers is your emp_registers_transition_ model with the lockout logic
from .models import emp_registers # Adjust this import based on your app's name
def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me', False)
        remember_me = True if remember_me == 'on' else False

        LOGIN_ATTEMPT_THRESHOLD = getattr(settings, 'LOGIN_ATTEMPT_THRESHOLD', 5)
        LOCKOUT_DURATION_HOURS = getattr(settings, 'LOCKOUT_DURATION_HOURS', 2)

        if not email or not password:
            messages.error(request, 'Email and password are required.', extra_tags='login')
            return render(request, 'login.html')

        try:
            user = emp_registers.objects.get(email=email)
            is_support_user = user.email.lower() == 'support@bispgmail.com'

            if str(user.job_status).lower() != 'active':
                messages.error(request, 'Your account is closed. Please contact administration.', extra_tags='login')
                return render(request, 'login.html')

            # --- Skip locking checks for support user ---
            if not is_support_user:
                if user.account_locked_until and user.account_locked_until <= timezone.now():
                    user.unlock_account()

                if user.is_locked():
                    remaining_seconds = (user.account_locked_until - timezone.now()).total_seconds()
                    hours, remainder = divmod(remaining_seconds, 3600)
                    minutes, _ = divmod(remainder, 60)

                    time_parts = []
                    if hours >= 1:
                        time_parts.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
                    if minutes >= 1:
                        time_parts.append(f"{int(minutes)} minute{'s' if minutes > 1 else ''}")
                    time_str = " and ".join(time_parts) if time_parts else "a moment"

                    messages.error(
                        request,
                        f"Your account is locked due to too many failed login attempts. Please try again after {time_str}.",
                        extra_tags='login'
                    )
                    return render(request, 'login.html')

            # --- Check password ---
            if check_password(password, user.password):
                if not is_support_user and (user.failed_login_attempts > 0 or user.account_locked_until):
                    user.unlock_account()

                request.session['user_id'] = user.id
                request.session['name'] = user.name
                request.session['postion'] = user.position.role
                request.session.set_expiry(604800 if remember_me else 0)

                return redirect('d2', id=user.id)

            else:
                if not is_support_user:
                    user.failed_login_attempts += 1
                    if user.failed_login_attempts >= LOGIN_ATTEMPT_THRESHOLD:
                        user.lock_account(duration_hours=LOCKOUT_DURATION_HOURS)
                        messages.error(
                            request,
                            f"Incorrect password. Too many failed attempts. Your account has been locked for {LOCKOUT_DURATION_HOURS} hours.",
                            extra_tags='login'
                        )
                    else:
                        messages.error(request, 'Invalid email or password.', extra_tags='login')
                    user.save()
                else:
                    # For support user, allow infinite wrong attempts with no penalty
                    messages.error(request, 'Invalid email or password.', extra_tags='login')

                return render(request, 'login.html')

        except emp_registers.DoesNotExist:
            messages.error(request, 'Invalid email or password.', extra_tags='login')
            return render(request, 'login.html')

    return render(request, 'login.html')


# staff/views.py (or wherever your views are located)

from django.core.mail import send_mail
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.hashers import make_password # For hashing passwords

# Assuming generate_random_password is a function that creates a random string

def generate_random_password():
    # Example simple random password generator (you might have your own)
    import random
    import string
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(characters) for i in range(12))


def Forget_passord(request):
    if request.method == "POST":
        email = request.POST.get("Email")
        user = emp_registers.objects.filter(email=email).first()

        if user:
            new_password = generate_random_password()
            user.password = make_password(new_password)  # Hash the new password
            user.save()

            try:
                send_mail(
                    "Password Reset Request for Your Account", # Clearer subject
                    f"Hello,\n\nYour new password is: {new_password}\n\nPlease log in and consider changing your password immediately.\n\nThank you.",
                    # Django automatically uses DEFAULT_FROM_EMAIL from settings.py
                    # If not set, it uses EMAIL_HOST_USER.
                    # You can explicitly set it here if you prefer: EMAIL_HOST_USER
                    None, # Use None here to let Django use DEFAULT_FROM_EMAIL or EMAIL_HOST_USER from settings
                    [email],
                    fail_silently=False, # Set to False to raise exceptions on email sending failure
                )
                messages.success(request, "A password reset email has been sent successfully.")
            except Exception as e:
                messages.error(request, f"Failed to send password reset email. Please try again later. Error: {e}")
                print(f"Error sending email: {e}") # Log the full error for debugging
        else:
            messages.error(request, "No account found with that email address.")

    # Redirect to the same page or a confirmation page
    return redirect("Forget_password")






def employee_registration(request, id):
    if 'user_id' not in request.session:
        return redirect('login')
    # Get the current employee by ID
    user = emp_registers.objects.filter(id=id).first()

    # If the user is not found, redirect to an error page
    if not user:
        messages.error(request, "User not found.", extra_tags="register")
        return redirect('some_error_page')  # Redirect to an error page or a safe place.

    # Fetch all positions (from RoleMaster) and departments (from DepartmentMaster)
    positions = RoleMaster.objects.all()
    departments = DepartmentMaster.objects.all()
    managers = emp_registers.objects.filter(position__role__iexact='Manager')
    # Handle POST request when form is submitted
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)

        # Check if the form is valid
        if form.is_valid():
            # Save the form without committing to the database yet
            employee_detail = form.save(commit=False)
            employee_detail.emp_id = user  # Set the foreign key to emp_registers
            employee_detail.save()

            # After saving emp and emp_detail

            eligible = False
            for leave in LeaveTypeMaster.objects.filter(leave_status=True):
                # Skip if specific_employees are set and current emp is not in them
                if leave.specific_employees.exists() and user not in leave.specific_employees.all():
                    continue

                # Gender and Marital Status match
                gender_match = leave.applicable_gender == 'All' or leave.applicable_gender == employee_detail.gender
                marital_match = leave.applicable_marital_status == 'All' or leave.applicable_marital_status == employee_detail.marriage_status

                # Department match
                dept_match = not leave.applicable_department.exists() or employee_detail.position.department in leave.applicable_department.all()

                if gender_match and marital_match and dept_match:
                    eligible = True
                    break  # Found a matching leave, no need to continue

            latest_employee_detail = emp_registers.objects.all().order_by('-id').first()
            emp, created = EmployeeDetail.objects.get_or_create(emp_id=latest_employee_detail)
            if eligible:
                initialize_leave_details(emp)

            # Success message
            messages.success(request, 'Employee registration successful!', extra_tags="register")
            return redirect('employee_registration', id=id)  # Redirect to the same page

        else:
            # Error message if form is not valid
            messages.error(request, 'Please correct the errors below.', extra_tags="register")

    else:
        # If it's a GET request, create an empty form
        form = EmployeeForm()

    # Render the template with the form, user, and the position/department choices
    return render(request, 'employee registration.html', {
        'form': form,
        'user': user,
        'id': id,
        'positions': positions,  # Pass positions to the template
        'departments': departments,  # Pass departments to the template,
        'managers':managers,
    })





def change_password(request):
    if 'user_id' not in request.session:
        return redirect('login')
    user_id=request.session.user_id
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match")
        else:
            emp = emp_registers.objects.get(id=request.session['user_id'])
            emp.password = make_password(new_password)
            emp.save()
            messages.success(request, "Password updated successfully")
            return redirect('/update_profile/',user_id =user_id)  # or wherever your profile page is
    return render(request, 'change_password.html')

# newproject/staff/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required

from .audit_logger import log_audit_action
from .models import Project, emp_registers, LeaveRecord # Your models used in views

@login_required
def view_all_projects(request):
    # Use request.session.user_id as the identifier
    user_identifier = request.session.get('user_id', 'Anonymous/Unknown')
    print(f"DEBUG: 'view_all_projects' view function called by {user_identifier}")
    projects = Project.objects.all()
    log_audit_action(user_identifier, "opened all projects list")
    return render(request, 'projects/project_list.html', {'projects': projects})

@login_required
def approve_leave_view(request, leave_id):
    leave_record = get_object_or_404(LeaveRecord, pk=leave_id)
    if request.method == 'POST':
        # ... logic to approve the leave ...
        leave_record.save() # This save triggers the post_save signal for LeaveRecord

        # Use request.session.user_id as the identifier
        user_identifier = request.session.get('user_id', 'Anonymous/Unknown')
        log_audit_action(user_identifier,
                         f"approved leave application (ID: {leave_id}) for {leave_record.emp_id.name}")
        return redirect('leave_list')
    return render(request, 'approve_leave_form.html', {'leave_record': leave_record})

@login_required
def generate_custom_report(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'unknown')
        # ... logic to generate the report ...
        user_identifier = request.session.get('user_id', 'Anonymous/Unknown')
        log_audit_action(user_identifier, f"generated a custom '{report_type}' report")
        return redirect('report_download_page')
    return render(request, 'reports/generate_report_form.html')





def update_profile_view(request):
    # Assuming 'emp_registers' is your custom user model or linked to Auth.User
    # You might need to adjust how you get the current emp_registers instance
    # For example, if request.user is an Auth.User, and emp_registers is linked via OneToOneField:
    # employee_instance = request.user.employee_profile # Or whatever your related_name is
    # For simplicity, if emp_registers is your actual user model:
    employee_instance = get_object_or_404(emp_registers, pk=request.user.pk)

    if request.method == 'POST':
        # ... process form data and save employee_instance ...
        employee_instance.save() # This save will trigger the post_save for emp_registers
        user_identifier = request.session.get('user_id', 'Anonymous/Unknown')
        log_audit_action(user_identifier, "updated own profile details")
        return redirect('profile_view')
    return render(request, 'profile_form.html', {'employee_instance': employee_instance})
#
# def update_profile(request,user_id):
#     if 'user_id' not in request.session:
#         return redirect('login')
#     emp = emp_registers.objects.get(id=request.session['user_id'])  # Get logged-in user
#     profile, created = EmployeeDetail.objects.get_or_create(emp_id=emp)  # Get or create profile
#     print('\n\n\n 257')
#     if request.method == 'POST':
#         profile.phone_number = request.POST.get('phone_number')
#         profile.guidance_phone_number = request.POST.get('guidance_phone_number')
#         profile.address = request.POST.get('address')
#         profile.father_guidance_name = request.POST.get('father_guidance_name')
#         profile.blood_group = request.POST.get('blood_group')
#         profile.permanent_address = request.POST.get('permanent_address')
#         profile.total_leave = request.POST.get('total_leave') or 0
#         profile.balance_leave = request.POST.get('balance_leave') or 0
#         profile.used_leave = request.POST.get('used_leave') or 0
#         profile.job_status = request.POST.get('job_status')
#
#         # Passport
#         profile.passport = request.POST.get('passport')
#         profile.passport_no = request.POST.get('passport_no')
#         profile.tel = request.POST.get('tel')
#         profile.nationality = request.POST.get('nationality')
#         profile.religion = request.POST.get('religion')
#         profile.marital_status = request.POST.get('marital_status')
#
#         # Emergency Contact
#         profile.primary_contact_name = request.POST.get('primary_contact_name')
#         profile.primary_relationship = request.POST.get('primary_relationship')
#         profile.primary_phone = request.POST.get('primary_phone')
#         profile.secondary_contact_name = request.POST.get('secondary_contact_name')
#         profile.secondary_relationship = request.POST.get('secondary_relationship')
#         profile.secondary_phone = request.POST.get('secondary_phone')
#
#         # Bank Info
#         profile.bank_name = request.POST.get('bank_name')
#         profile.bank_account_no = request.POST.get('bank_account_no')
#         profile.ifsc_code = request.POST.get('ifsc_code')
#         profile.pan_no = request.POST.get('pan_no')
#
#         # Image Upload
#         if 'profile_image' in request.FILES:
#             profile.profile_image = request.FILES['profile_image']
#
#         profile.save()
#         education = Education.objects.filter(emp_id=emp.id).first()
#         experience = Experience.objects.filter(emp_id=emp.id).first()
#         # Education & Experience
#         education.degree = request.POST.get('degree')
#         education.institution = request.POST.get('institution')
#         education.year_of_passing = request.POST.get('year_of_passing') or None
#         education.grade = request.POST.get('grade')
#         print('\n\n\n\nhcj', education.degree)
#         education.save()
#
#         # Save or create experience
#         if not experience:
#             experience = Experience(emp_id=emp.id)
#         experience.organization = request.POST.get('organization')
#         experience.position = request.POST.get('position')
#         experience.from_date = request.POST.get('from_date') or None
#         experience.to_date = request.POST.get('to_date') or None
#         experience.description = request.POST.get('description')
#         experience.save()
#
#         if 'document_file' in request.FILES:
#             doc_file = request.FILES['document_file']
#             doc_name = request.POST.get('document_name')
#             doc_type = request.POST.get('document_type')
#             if doc_name and doc_type:
#                 Document.objects.create(
#                     emp_id=profile.emp_id,
#                     document_name=doc_name,
#                     document_type=doc_type,
#                     document_file=doc_file
#                 )
#                 messages.success(request, "Document uploaded.")
#                 return redirect('update_profile')
#         messages.success(request, "Profile updated successfully.")
#         return redirect('update_profile')
#
#     return render(request, 'update_profile.html', {'profile': profile})



def delete_document(request, doc_id):
    doc = Document.objects.get(id=doc_id)
    if doc.emp_id.id == request.user.emp_id.id:
        doc.delete()
        messages.success(request, "Document deleted.")
    return redirect('update_profile')



def project(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    projects = Project.objects.prefetch_related('team_members').filter(
        Q(admin=request.session['name']) |
        Q(manager=request.session['user_id']) |
        Q(team_members__emp_id=user_id)
    ).order_by('-id').distinct()
    total_projects = projects.count()

    context = {
        'projects': projects,
        'total_projects': total_projects
    }
    return render(request, 'project.html', context)

from django import template

register = template.Library()

@register.filter
def status_color(status):
    color_map = {
        "hold": "purple",
        "complete": "green",
        "pending": "red",
        "claim-complete": "skyblue",
        "incomplete": "orange",
    }
    return color_map.get(status.lower().replace(" ", "-"), "black")



def forgot_password(request):
    return render(request, 'forgot_password.html')
# def employee_registration(request,id):
#     user =emp_registers.objects.get(id=id)
#
#     if request.method == 'POST':
#         name = request.POST.get('name').strip()
#         email = request.POST.get('email').strip()
#         password = request.POST.get('password').strip()
#         rpassword = request.POST.get('rpassword').strip()
#         position = request.POST.get('position').strip()
#         department = request.POST.get('department').strip()
#         joindate = request.POST.get('joindate').strip()
#         reportto = request.POST.get('reportto').strip()
#         gender = request.POST.get('gender').strip()
#         marriage_status = request.POST.get('marriage_status').strip()
#         aadhar_no = request.POST.get('aadhar_no').strip()
#         dob = request.POST.get('dob').strip()
#         nationality = request.POST.get('nationality').strip()
#         religion = request.POST.get('religion').strip()
#         profile_pic = request.FILES.get('profile_pic')
#
#
#         # Validation checks
#         if not all([name, email, password, rpassword, position, department, joindate, dob, gender, aadhar_no, nationality, religion]):
#             messages.error(request, 'All fields are required!')
#             return redirect('employee_registration',id=id)
#
#         if not re.match(r'^[a-zA-Z ]+$', name):
#             messages.error(request, 'Invalid name. Only letters and spaces are allowed.')
#             return redirect('employee_registration',id=id)
#         if name.startswith(' '):
#             messages.error(request, 'Name should not start with a space.')
#             return redirect('employee_registration',id=id)
#
#         if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
#             messages.error(request, 'Invalid email address.')
#             return redirect('employee_registration',id=id)
#
#         if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*]', password):
#             messages.error(request, 'Password must be at least 8 characters, including one uppercase letter, one number, and one special character.')
#             return redirect('employee_registration',id=id)
#
#         if password != rpassword:
#             messages.error(request, 'Passwords do not match.')
#             return redirect('employee_registration',id=id)
#
#         try:
#             dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
#             joindate_date = datetime.strptime(joindate, '%Y-%m-%d').date()
#
#             if dob_date >= datetime.today().date():
#                 messages.error(request, 'Invalid Date of Birth.')
#                 return redirect('employee_registration',id=id)
#             if dob_date < date(1980, 1, 1):
#                 messages.error(request, 'date of birth not more than 1980.')
#                 return redirect('employee_registration',id=id)
#
#
#             if dob_date > datetime.today().date() - timedelta(days=18*365):
#                 messages.error(request, 'Employee must be at least 18 years old.')
#                 return redirect('employee_registration',id=id)
#
#             # if joindate_date > datetime.today().date():
#             #     messages.error(request, 'Joining date cannot be in the future.')
#             #     return redirect('employee_registration',id=id)
#
#             if joindate_date < datetime(2025, 1, 1).date():
#                 messages.error(request, 'Joining date cannot be before January 1, 2025.')
#                 return redirect('employee_registration',id=id)
#             if user.position.lower() == 'manager':
#                 if position == 'Manager' or position == 'HR':
#                     messages.error(request, 'Manager only add employee position ')
#                     return redirect('employee_registration', id=id)
#             if user.position.lower()== 'employee':
#                 messages.error(request,message="employee are not allow member")
#                 return ()
#
#
#             # if joindate_date > datetime.today().date():
#             #     messages.error(request, 'Joining date cannot be after the current date.')
#             #     return redirect('employee_registration',id=id)
#         except ValueError:
#             messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
#             return redirect('employee_registration',id=id)
#
#         if not re.match(r'^\d{12}$', aadhar_no):
#             messages.error(request, 'Invalid Aadhar number. It must be 12 digits.')
#             return redirect('employee_registration',id=id)
#
#         if emp_registers.objects.filter(email=email).exists():
#             messages.error(request, 'Email already exists!')
#             return redirect('employee_registration',id=id)
#
#         # Save to database
#         e1 = emp_registers(
#             name=name,
#             email=email,
#             password=password,
#             position=position,
#             department=department,
#             joindate=joindate_date,
#             reportto=reportto,
#             gender=gender,
#             marriage_status=marriage_status,
#             aadhar_no=aadhar_no,
#             dob=dob_date,
#             nationality=nationality,
#             religion=religion,
#         profile_pic = profile_pic
#         )
#         e1.save()
#         update_total_leaves()
#         messages.success(request, 'Employee registration successful!')
#        # time.sleep(3)
#         return redirect('employee_registration',id=id)
#
#     return render(request,'employee registration.html',{'user': user, 'id': id})





from django.utils.dateparse import parse_date


def add_project_view(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    user_id = request.session.get('user_id')
    try:
        emp = emp_registers.objects.get(id=user_id)
        admin_name = emp.name
    except emp_registers.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect('login')


    employee_members = emp_registers.objects.filter(position__role__iexact='Employee')
    rate_status_list = RateStatusMaster.objects.all()
    priority_list = PriorityMaster.objects.all()
    status_list = StatusMaster.objects.all()
    managers = emp_registers.objects.filter(position__role__iexact='Manager')

    if request.method == "POST":
        pname = request.POST.get('pname')
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        rate = request.POST.get('rate')
        rate_status = request.POST.get('rate_status')
        priority = request.POST.get('priority')
        description = request.POST.get('description')
        client = request.POST.get('client')
        manager = request.POST.get('manager')
        team_member_ids = request.POST.getlist('team_members')

        form_data = request.POST.copy()

        if not rate:
            messages.error(request, "Rate is required.")
            return render(request, 'add_project.html', {
                'status_list': status_list,
                'rate_status_list': rate_status_list,
                'priority_list': priority_list,
                'managers': managers,
                'employee_members': employee_members,
                'form_data': form_data
            })

        try:
            rate_val = float(rate)
            if rate_val < 0:
                messages.error(request, "Rate cannot be negative.")
                return render(request, 'add_project.html', {
                    'status_list': status_list,
                    'rate_status_list': rate_status_list,
                    'priority_list': priority_list,
                    'managers': managers,
                    'employee_members': employee_members,
                    'form_data': form_data
                })
        except ValueError:
            messages.error(request, "Invalid rate value.")
            return render(request, 'add_project.html', {
                'status_list': status_list,
                'rate_status_list': rate_status_list,
                'priority_list': priority_list,
                'managers': managers,
                'employee_members': employee_members,
                'form_data': form_data
            })

        # Validate start date
        if start_date:
            try:
                sd = parse_date(start_date)
                today = date.today()
                if sd < today:
                    messages.error(request, "Start date cannot be before today.")
                    return render(request, 'add_project.html', {
                        'status_list': status_list,
                        'rate_status_list': rate_status_list,
                        'priority_list': priority_list,
                        'managers': managers,
                        'employee_members': employee_members,
                        'form_data': form_data
                    })
            except Exception:
                messages.error(request, "Invalid start date format.")
                return render(request, 'add_project.html', {
                    'status_list': status_list,
                    'rate_status_list': rate_status_list,
                    'priority_list': priority_list,
                    'managers': managers,
                    'employee_members': employee_members,
                    'form_data': form_data
                })

        # Validate date range
        if start_date and end_date:
            try:
                sd = parse_date(start_date)
                ed = parse_date(end_date)
                if ed < sd:
                    messages.error(request, "End date cannot be before start date.")
                    return render(request, 'add_project.html', {
                        'status_list': status_list,
                        'rate_status_list': rate_status_list,
                        'priority_list': priority_list,
                        'managers': managers,
                        'employee_members': employee_members,
                        'form_data': form_data
                    })
            except Exception:
                messages.error(request, "Invalid date format.")
                return render(request, 'add_project.html', {
                    'status_list': status_list,
                    'rate_status_list': rate_status_list,
                    'priority_list': priority_list,
                    'managers': managers,
                    'employee_members': employee_members,
                    'form_data': form_data
                })

        # Validate manager

        if manager:
            try:
                manager = emp_registers.objects.get(id=manager)
            except emp_registers.DoesNotExist:
                messages.error(request, "Invalid Manager selected.")
                return render(request, 'add_project.html', {
                    'status_list': status_list,
                    'rate_status_list': rate_status_list,
                    'priority_list': priority_list,
                    'managers': managers,
                    'employee_members': employee_members,
                    'form_data': form_data
                })

        rate_status_obj = None
        if rate_status:
            try:
                rate_status_obj = RateStatusMaster.objects.get(id=rate_status)
            except RateStatusMaster.DoesNotExist:
                messages.error(request, "Invalid rate status selected.")
                return render(request, 'add_project.html', {
                    'status_list': status_list,
                    'rate_status_list': rate_status_list,
                    'priority_list': priority_list,
                    'managers': managers,
                    'employee_members': employee_members,
                    'form_data': form_data
                })

        try:
            priority_obj = PriorityMaster.objects.get(id=priority)
        except PriorityMaster.DoesNotExist:
            messages.error(request, "Invalid priority selected.")
            return render(request, 'add_project.html', {
                'status_list': status_list,
                'rate_status_list': rate_status_list,
                'priority_list': priority_list,
                'managers': managers,
                'employee_members': employee_members,
                'form_data': form_data
            })

        # Create project
        project = Project.objects.create(
            emp_id=emp,
            pname=pname,
            start_date=start_date,
            end_date=end_date,
            rate=float(rate),
            rate_status=rate_status_obj,
            priority=priority_obj,
            description=description,
            admin=admin_name,
            manager=manager,
            client=client,
            status=StatusMaster.objects.get(id=1)
        )

        # Add team members
        team_members = []
        for emp_id in team_member_ids:

            employee = emp_registers.objects.filter(id=emp_id).first()
            if employee:
                print(employee.name)
                member, _ = Member.objects.get_or_create(
                    emp_id=employee,
                    defaults={
                        'name': employee.name,
                        'email': employee.email
                    }
                )
                member.save()
                team_members.append(member)


        project.team_members.set(team_members)


        messages.success(request, "Project created successfully!")
        return redirect('project', user_id=user_id)

    return render(request, 'add_project.html', {
        'status_list': status_list,
        'rate_status_list': rate_status_list,
        'priority_list': priority_list,
        'managers': managers,
        'employee_members': employee_members
    })





def add_employee(request):
    return redirect('employee registration')





# views.py
def employee_list(request):
    employees = emp_registers.objects.filter(job_status=1)
    departments = DepartmentMaster.objects.all()
    return render(request, 'employee_list.html', {
        'employees': employees,
        'department_choices': departments
    })

def deactivate_employee(request, emp_id):
    try:
        data = json.loads(request.body)
        status = data.get('status')

        if status == 'deactive':  # <-- updated check
            job_status=JobStatusMaster.objects.get(status='deactive')
            employee = emp_registers.objects.get(id=emp_id)
            employee.job_status = job_status  # <-- updated field value
            employee.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
    except emp_registers.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Employee not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def deactive_employee_list(request):
    employees = emp_registers.objects.filter(job_status=4)
    departments = DepartmentMaster.objects.all()
    return render(request, 'deactive_employee_list.html', {
        'employees': employees,
        'department_choices': departments
    })

def activate_employee(request, emp_id):
    try:
        data = json.loads(request.body)
        status = data.get('status')

        if status == 'active':  # <-- updated check
            job_status=JobStatusMaster.objects.get(status='active')
            employee = emp_registers.objects.get(id=emp_id)
            employee.job_status = job_status  # <-- updated field value
            employee.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'Invalid status'})
    except emp_registers.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Employee not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
# views.py

from django.views.decorators.http import require_POST

def employee_lock_status_view(request):
    employees = emp_registers.objects.filter(job_status=1)
    return render(request, 'employee_lock_status.html', {'employees': employees})


def unlock_account_view(request, emp_id):
    try:
        employee = emp_registers.objects.get(id=emp_id)
        employee.failed_login_attempts = 0
        employee.account_locked_until = None
        employee.save()
        messages.success(request, f"Account for {employee.name} has been unlocked.")
    except emp_registers.DoesNotExist:
        messages.error(request, "Employee not found.")
    return redirect('employee_lock_status')

from django import template

register = template.Library()


def first_name(value):
    """Returns the first word in the string (assumed to be the first name)."""
    if isinstance(value, str):
        return value.split()[0]
    return value



import json
from django.core.serializers.json import DjangoJSONEncoder


def leave_record_view(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')  # 'log

    # Extract filter values from request
    name = request.GET.get('name', '')
    user_id = request.GET.get('id', '')
    date = request.GET.get('date', '')
    employee_type = request.GET.get('employee_type', '')
    department = request.GET.get('department', '')
    leave_type = request.GET.get('leave_type', '')
    approve_status = request.GET.get('approve_status', '')
    approve_by = request.GET.get('approve_by', '')

    # Apply filters using Q objects
    query = Q()
    if name:
        query &= Q(name__icontains=name)
    if user_id:
        query &= Q(id=user_id)
    if date:
        query &= Q(date=date)
    if employee_type:
        query &= Q(employee_type=employee_type)
    if department:
        query &= Q(department=department)
    if leave_type:
        query &= Q(leave_type=leave_type)
    if approve_status:
        query &= Q(approve_status=approve_status)
    if approve_by:
        query &= Q(approve_by__icontains=approve_by)

    # Retrieve filtered records
    leave_records = LeaveRecord.objects.filter(query).order_by('-id')

    # Serialize half-day info for each leave record
    leave_data = []
    for leave in leave_records:
        half_day_entries = leave.half_day.all()
        half_day_info = [{
            'date': hd.half_day_date.strftime('%Y-%m-%d'),
            'type': str(hd.half_day_type.part)  # Assuming `part` contains "First Half" or "Second Half"
        } for hd in half_day_entries]

        leave_data.append({
            'id': leave.id,
            'no_of_days': str(leave.no_of_days),
            'half_day_info': half_day_info
        })

    # Pass serialized data to template
    return render(request, 'leave_record.html', {
        'leave_record': leave_records,
        'leave_data_json': json.dumps(leave_data, cls=DjangoJSONEncoder),
        'today': now().date()
    })


import random
def set_page_size_preference(request):
    if request.method == "POST":
        page_size = request.POST.get("page_size")
        if page_size:
            request.session["preferred_page_size"] = page_size
            return JsonResponse({"success": True})
    return JsonResponse({"success": False})




def delete_employee(request, id):
    if 'user_id' not in request.session:
        return redirect('login')  # 'log
    employee = get_object_or_404(emp_registers, id=id)
    employee.delete()
    messages.success(request, "emp_registers deleted successfully!")
    return redirect('employee_list')

from .models import Video


from moviepy import VideoFileClip
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
import os
import uuid
def learning_videos_dashboard(request):
    categories = [choice[0] for choice in Video.CATEGORY_CHOICES]

    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category')
        file = request.FILES.get('file')

        if title and category and file:
            Video.objects.create(title=title, category=category, video=file)
            if title and category and file:
                # Save video first
                video_obj = Video.objects.create(title=title, category=category, video=file)

                # Generate thumbnail
                try:
                    clip = VideoFileClip(video_obj.video.path)
                    frame = clip.get_frame(0)  # Get the first frame
                    image = Image.fromarray(frame)
                    buffer = BytesIO()
                    image.save(buffer, format='JPEG')
                    buffer.seek(0)

                    thumbnail_filename = f"{uuid.uuid4().hex}.jpg"
                    video_obj.thumbnail.save(thumbnail_filename, ContentFile(buffer.read()), save=True)
                    clip.close()
                except Exception as e:
                    print(f"Thumbnail generation failed: {e}")

                return redirect('learning_videos_dashboard')

            return redirect('learning_videos_dashboard')

    videos_by_category = {
        cat: Video.objects.filter(category=cat) for cat in categories
    }

    return render(request, 'learning_videos_dashboard.html', {
        'categories': categories,
        'videos_by_category': videos_by_category
    })


# views.py
from django.shortcuts import redirect, get_object_or_404
from .models import Video
import os
from django.conf import settings


def delete_video(request, video_id):
    if request.method == 'POST':
        video = get_object_or_404(Video, id=video_id)

        # Remove video file from media folder
        if video.video and os.path.isfile(video.video.path):
            os.remove(video.video.path)

        # Delete video entry from database
        video.delete()

    return redirect('learning_videos_dashboard')  # replace with actual view name
from moviepy import VideoFileClip
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import os
from io import BytesIO
from PIL import Image

def add_learning_video(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        category = request.POST.get('category')
        video_file = request.FILES.get('file')

        video = LearningVideo(title=title, category=category, video=video_file)
        video.save()

        # Generate thumbnail

        return redirect('your_learning_video_page_name')

    ...


# views.py

from django.shortcuts import render




from datetime import datetime, timedelta
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import LeaveRecord, LeaveHalfDay, HalfDayTypeMaster, LeaveTypeMaster, LeaveStatusMaster, Holiday, emp_registers, EmployeeDetail

def apply_leave(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    try:
        employee = EmployeeDetail.objects.get(emp_id=user_id)
        emp = emp_registers.objects.get(id=user_id)
    except EmployeeDetail.DoesNotExist:
        messages.error(request, "Employee details not found.")
        return redirect('login')

    leave_types = LeaveTypeMaster.objects.filter(leave_status=True)

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type_id = int(request.POST.get('leave_type'))
        reason = request.POST.get('reason')

        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        leave_type = LeaveTypeMaster.objects.get(id=leave_type_id)
        leave_code = leave_type.leavecode
        compensatory_leave = request.POST.get('compensatory_leave', False) == 'on'
        compensatory_leave_reason = request.POST.get('compensatory_leave_reason', None)
        document = request.FILES.get('document', None)

        half_day_data = request.POST.getlist('half_day[]')
        half_day_dict = {}
        for entry in half_day_data:
            if entry:
                date, half = entry.rsplit('-', 1)
                half_day_dict[date] = half

        leave_days = 0.0
        current_date = start_date
        holidays = set(Holiday.objects.filter(date__range=[start_date, end_date]).values_list('date', flat=True))

        def is_weekend_off(date):

            if date.weekday() == 6:  # Sunday
                return True
            if date.weekday() == 5:  # Saturday
                week_number = (date.day - 1) // 7 + 1
                return week_number in [2, 3]  # 2nd or 3rd Saturday
            return False

        while current_date <= end_date:
            str_date = str(current_date)
            is_edge_date = current_date == start_date or current_date == end_date

            if not is_edge_date and not leave_type.count_weekends:
                if is_weekend_off(current_date):
                    current_date += timedelta(days=1)
                    continue

            if current_date in holidays and not leave_type.count_holidays:
                current_date += timedelta(days=1)
                continue

            if str_date in half_day_dict:
                leave_days += 0.5
            else:
                leave_days += 1.0

            current_date += timedelta(days=1)

        leave_details = employee.leave_details or {}

        if leave_code not in leave_details:
            messages.error(request, f"No leave details found for {leave_code}.")
            return redirect('apply_leave', user_id=user_id)

        available_balance = leave_details[leave_code].get('balance', 0)

        # Check for balance
        if available_balance < leave_days:
            messages.error(request, "Insufficient leave balance.", extra_tags='apply_leave')
            return redirect('apply_leave', user_id=user_id)

        pending_status = LeaveStatusMaster.objects.filter(status__iexact='pending').first()

        # Create the LeaveRecord
        leave_record = LeaveRecord.objects.create(
            emp_id=employee.emp_id,
            start_date=start_date,
            end_date=end_date,
            no_of_days=leave_days,
            leave_type=leave_type,
            reason=reason,
            approval_status=pending_status,
            compensatory_leave=compensatory_leave,
            compensatory_leave_reason=compensatory_leave_reason,
            document=document
        )

        # Create LeaveHalfDay entries and link via ManyToMany
        for entry in half_day_data:
            if entry:
                date_str, half = entry.rsplit('-', 1)
                date = datetime.strptime(date_str, '%Y-%m-%d').date()
                try:
                    half_day_obj = HalfDayTypeMaster.objects.get(part=half)
                    leave_half_day = LeaveHalfDay.objects.create(
                        half_day_type=half_day_obj,
                        half_day_date=date
                    )
                    leave_record.half_day.add(leave_half_day)  # Link via M2M
                except HalfDayTypeMaster.DoesNotExist:
                    continue

        messages.success(request, "Leave application submitted successfully!")
        return redirect('leave_dashboard', user_id=user_id)

    leave_details = employee.leave_details
    leave_types = LeaveTypeMaster.objects.filter(leave_status=True)
    leave_details_summary = {}
    new_leave_type = []

    for leave_code, details in leave_details.items():
        if leave_code not in [leave.leavecode for leave in leave_types]:
            continue
        if details.get('total', 0) == 0 and details.get('used', 0) == 0 and details.get('balance', 0) == 0:
            continue
        leave_details_summary[leave_code] = {
            'total': details.get('total', 0),
            'used': details.get('used', 0),
            'balance': details.get('balance', 0)
        }
        new_leave_type.append(LeaveTypeMaster.objects.get(leavecode=leave_code))

    new_leave_type_queryset = LeaveTypeMaster.objects.filter(id__in=[leave.id for leave in new_leave_type])
    return render(request, 'apply_leave.html', {
        'leave_details_summary': leave_details_summary,
        'new_leave_type_queryset': new_leave_type_queryset
    })



def update_total_leaves():

    current_year = date.today().year
    employees = emp_registers.objects.filter(job_status=1)  # Fetch all employees from emp_registers

    if not employees:
        return JsonResponse({"status": "error", "message": "No employee records found."})

    for emp in employees:
        # Calculate total leaves based on position and join date
        if emp.position.role  == 'HR':
            # If position is HR, they get 18 leaves no matter when they join
            total_leave = 18
        else:
            # For other positions, calculate pro-rated leave
            if emp.joindate.year < current_year:
                total_leave = 12  # Full leave for employees who joined earlier in the year
            else:
                remaining_months = 13 - emp.joindate.month # Remaining months in the year
                total_leave = (remaining_months / 12) * 12  # Pro-rate the leaves based on remaining months

        # Ensure we create or update EmployeeDetail record for each employee
        # Use `get_or_create` to fetch or create the record
        employee_detail, created = EmployeeDetail.objects.get_or_create(emp_id=emp)

        # If the record exists (created is False), we update the total_leave value
        if not created:
            # Check if the total_leave value is different and needs an update
            if employee_detail.total_leave != total_leave:
                employee_detail.total_leave = total_leave
                employee_detail.save()  # Save only if the value has changed

        else:
            # If it's created, we just set the total_leave and save
            employee_detail.total_leave = total_leave
            employee_detail.save()

        # Print for debugging
        print(f"Total leave {'created' if created else 'updated'} for Emp ID {emp.id} ({emp.email}): {total_leave}")

    print("Leave update completed.")

    # Return a JsonResponse or any other response if needed
    return JsonResponse({"status": "success", "message": "Leave updated successfully"})

def update_leaves_view(request):
    update_total_leaves()
    emp =EmployeeDetail.objects.all()
    for e in emp:
        initialize_leave_details(e)
    return JsonResponse({'status': 'Total leaves updated successfully!'})










# def update_leave_status(request):
#     if request.method == "POST":
#         leave_id = request.POST.get("id")  # Get leave record ID from POST request
#         action = request.POST.get("action")  # Get action (approve/reject/withdraw)
#
#         # Get logged-in user ID from session
#         user_id = request.session.get("user_id")
#         if not user_id:
#             return JsonResponse({"error": "User not logged in"}, status=403)
#
#         # Validate and convert leave_id to an integer
#         if not leave_id or not leave_id.isdigit():
#             return JsonResponse({"error": "Invalid leave ID"}, status=400)
#
#         leave_id = int(leave_id)  # Convert to integer after validation
#
#         try:
#             # Fetch the leave record
#             leave = LeaveRecord.objects.get(id=leave_id)
#
#             # Perform action based on request
#             if action == "approve":
#                 leave.approval_status = "Approved"
#             elif action == "reject":
#                 leave.approval_status = "Rejected"
#             elif action == "withdraw":
#                 if leave.start_date >= now().date():  # Only allow withdrawal before start date
#                     leave.approval_status = "Withdrawn"
#                     leave.save()  # Save status change
#
#                     # Get the employee making the request
#                     approver = get_object_or_404(emp_registers, id=user_id)
#
#                     # Fetch employee details
#                     emp = get_object_or_404(EmployeeDetail, emp_id=approver.id)
#
#                     # Update balance leave
#                     emp.balance_leave += leave.no_of_leaves
#                     emp.save()
#                 else:
#                     return JsonResponse({"error": "Cannot withdraw past leave"}, status=400)
#
#             leave.save()  # Save approval/rejection changes
#             return JsonResponse({"status": leave.approval_status})
#
#         except LeaveRecord.DoesNotExist:
#             return JsonResponse({"error": "Leave record not found"}, status=404)
#
#     return JsonResponse({"error": "Invalid request"}, status=400)







def leave_dashboard(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    # Ensure the user is logged in
    # if 'user_id' not in request.session:
    #     return redirect('/login/')

    # Get logged-in user details
    username = request.session.get('name')
    user_id=request.session.get('user_id')
    today = now().date()

    # Fetch leave records for the logged-in employee
    leave_records = LeaveRecord.objects.filter(emp_id=user_id).order_by('-id')
    emp=emp_registers.objects.filter(id=user_id)
    # Prepare data to be passed to the template
    leave_data = []


    # ✅ Fetch all half-day entries related to this leave record
    # half_days = LeaveHalfDay.objects.filter(leave_record=leave_records.id)
    for leave in leave_records:
        try:

            leave_type_obj = LeaveTypeMaster.objects.get(id=leave.leave_type.id)

            emp_data = emp_registers.objects.get(id=leave.emp_id.id)

            half_day_list = [(half.half_day_date, half.half_day_type.part) for half in leave.half_day.all()]
            report_to = emp_data.reportto if emp_data.reportto else 'Not Assigned'
            leave_data.append({
                's_no': len(leave_data) + 1,  # Serial number
                'name': emp_data.name,
                'current_date': leave.created_at,  # Corrected to use dot notation
                'start_date': leave.start_date,  # Corrected to use dot notation
                'end_date': leave.end_date,  # Corrected to use dot notation
                'no_of_leaves': leave.no_of_days,  # Corrected to use dot notation
                'reason': leave.reason,  # Corrected to use dot notation
                'approval_status': leave.approval_status,  # Corrected to use dot notation
                'report_to': report_to,
                'leave_id': leave.id,  # Corrected to use dot notation
                'approved_by': leave.approved_by,  # Corrected to use dot notation
                'approve_reason': leave.approve_reason,  # Corrected to use dot notation
                'compensatory_leave': leave.compensatory_leave,  # Corrected to use dot notation
                'compensatory_leave_reason': leave.compensatory_leave_reason,  # Corrected to use dot notation
                'leave_type': leave_type_obj,  # leave_type is a LeaveTypeMaster object
                'half_day': half_day_list,  # Corrected to use previously generated half_day_list
                'department':emp_data.department.name,
                'id':leave.id
            })

            # Same field as in LeaveRecord,
                # 'half_day': leave['half_day'],  # Same field as in LeaveRecord,
                # 'half_day': list(leave.leavehalfday_set.values('half_day_date', 'half_day_type__part')),
                # 'half_day': [(half.half_day_date, half.half_day_type.part) for half in half_days],

        except emp_registers.DoesNotExist:
            continue  # Skip if employee data not found

    # Render the dashboard template with the leave data

    # If this is an AJAX request, return JSON response with updated data

    return render(request, 'leave_dashboard.html', {
        'leave_data': leave_data,
        'username': username,
        'today': today,'emp':emp,
        'user_id':user_id,
    })

from django.http import JsonResponse
from .models import Task  # Replace with your actual Task model

def get_tasks(request):
    project_id = request.GET.get('project_id')
    user_id = request.GET.get('user_id')
    print(user_id)

    if project_id:

        tasks = Task.objects.filter(
            project_id=project_id,
            assigned_to__emp_id=user_id
        ).exclude(
            status__status__iexact='Complete'
        ).values('id', 'title')
        task_list = [{'id': task['id'], 'name': task['title']} for task in tasks]

        return JsonResponse({'tasks': task_list})
    return JsonResponse({'tasks': []})



def update_leave_status(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    approver = emp_registers.objects.get(id=user_id)

    if request.method == "POST":
        leave_id = request.POST.get("leave_id")
        action = request.POST.get("action")
        reason = request.POST.get("approve_reason", "")

        leave_record = get_object_or_404(LeaveRecord, id=leave_id)
        employee = EmployeeDetail.objects.get(emp_id=leave_record.emp_id.id)
        leave_type = leave_record.leave_type
        leave_code = leave_type.leavecode  # Make sure this matches what's used in leave_details

        status_obj = LeaveStatusMaster.objects.filter(status=action).first()

        if not status_obj:
            return JsonResponse({"error": f"'{action}' status not configured."}, status=500)

        previous_status = leave_record.approval_status.status if leave_record.approval_status else ""
        leave_details = employee.leave_details or {}

        # Ensure leave_code exists in leave_details
        if leave_code not in leave_details:
            leave_details[leave_code] = {'total': 0, 'used': 0, 'balance': 0}

        # Withdraw logic
        if action == "Withdrawn":
            if now().date() > leave_record.start_date:
                return JsonResponse({"error": "Cannot withdraw, start date has passed."}, status=400)

            if previous_status == "Approved" and not leave_record.compensatory_leave:
                leave_details[leave_code]['used'] = max(0, leave_details[leave_code]['used'] - leave_record.no_of_days)
                leave_details[leave_code]['balance'] += leave_record.no_of_days
                # Cap the balance at total
                leave_details[leave_code]['balance'] = min(
                    leave_details[leave_code]['balance'],
                    leave_details[leave_code]['total'])

        # Approve logic
        elif action == "Approved":
            if previous_status != "Approved" and not leave_record.compensatory_leave:
                if leave_details[leave_code]['balance'] < leave_record.no_of_days:
                    return JsonResponse({"error": "Insufficient leave balance."}, status=400)
                leave_details[leave_code]['used'] += leave_record.no_of_days
                leave_details[leave_code]['balance'] -= leave_record.no_of_days

                leave_details[leave_code]['used'] = min(
                    leave_details[leave_code]['used'],
                    leave_details[leave_code]['total']
                )
                leave_details[leave_code]['balance'] = max(0, leave_details[leave_code]['balance'])

        # Reject logic
        elif action == "Rejected":
            # if previous_status == "Approved":
            #     leave_details[leave_code]['used'] -= leave_record.no_of_days
            #     leave_details[leave_code]['balance'] += leave_record.no_of_days
            leave_record.approve_reason = reason


        # Save the updated leave_details and leave record
        employee.leave_details = leave_details
        employee.save()

        leave_record.approval_status = status_obj
        leave_record.approved_by = approver.name
        leave_record.save()

        return JsonResponse({
            "status": leave_record.approval_status.status,
            "approved_by": leave_record.approved_by
        })

    return JsonResponse({"error": "Invalid request"}, status=400)

from django.shortcuts import render, redirect
from .models import Holiday
from django.utils.dateparse import parse_date

def holiday_list_view(request):
    if request.method == 'POST':
        name = request.POST.get('holiday_name')
        date_str = request.POST.get('holiday_date')

        if name and date_str:
            date = parse_date(date_str)
            Holiday.objects.create(name=name, date=date)

        return redirect('holiday_list_view')

    holidays = Holiday.objects.all().order_by('date')
    return render(request, 'holiday_list.html', {'holidays': holidays})

from django.http import JsonResponse
from .models import Task

# def get_tasks(request):
#     project_id = request.GET.get('project_id')
#     if project_id:
#         tasks = Task.objects.filter(project_id=project_id)  # Assuming Task model has a project_id field
#         task_data = [{'id': task.id, 'title': task.title} for task in tasks]
#         return JsonResponse({'tasks': task_data})
#     return JsonResponse({'tasks': []})  # Return empty tasks if no project_id



from django.utils import timezone

def initialize_leave_details(emp_detail):

    current_date = timezone.now().date()
    leave_data = emp_detail.leave_details or {}

    is_jan_first = current_date.month == 1 and current_date.day == 1
    last_renewed = leave_data.get("_last_renewed")

    leave_types = LeaveTypeMaster.objects.all()

    for leave_type in leave_types:
        code = leave_type.leavecode or leave_type.name[:3].upper()

        # Eligibility checks
        if leave_type.applicable_gender != 'All' and leave_type.applicable_gender != emp_detail.gender:
            continue

        if leave_type.applicable_marital_status != 'All' and leave_type.applicable_marital_status != emp_detail.marital_status:
            continue

        department = emp_detail.emp_id.department
        if leave_type.applicable_department.exists() and not leave_type.applicable_department.filter(pk=department.pk).exists():
            continue

        if leave_type.specific_employees.exists() and not leave_type.specific_employees.filter(id=emp_detail.id).exists():
            continue

        if leave_type.start_from and leave_type.end_from:
            if not (leave_type.start_from <= current_date <= leave_type.end_from):
                continue

        total = leave_type.max_days_allowed or 4

        # If leave already exists
        if code in leave_data:
            existing = leave_data[code]

            if leave_type.carry_forward and is_jan_first and last_renewed != str(current_date):
                # Carry forward only on Jan 1st and not done already
                prev_balance = existing.get("balance", 0)
                leave_data[code]["used"] = 0
                leave_data[code]["balance"] = prev_balance
                leave_data[code]["total"] = prev_balance + total
            elif not leave_type.carry_forward:
                # Reset values if not carry forward
                leave_data[code]["used"] = 0
                leave_data[code]["balance"] = total
                leave_data[code]["total"] = total
            # Else: don't touch anything if not Jan 1st and carry forward
        else:
            # First time adding this leave

            leave_data[code] = {
                "used": 0,
                "balance": total,
                "total": total
            }


    # Set renewal marker only on Jan 1st
    if is_jan_first:
        leave_data["_last_renewed"] = str(current_date)

    emp_detail.leave_details = leave_data
    emp_detail.save()
    print(f"Leave details updated for employee {emp_detail.id}: {emp_detail.leave_details}")








def is_leave_type_valid_today(leave_type, today):

    # Check start and end date validity only if given
    if leave_type.start_from and today < leave_type.start_from.date():
        return False
    if leave_type.end_from and today > leave_type.end_from.date():
        return False
    return True


def add_leave_type(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.method == 'POST':
        # Collecting form data
        leave_name = request.POST.get('name')
        leave_code = request.POST.get('leavecode')
        payable = request.POST.get('payable') == 'True'

        # Applicable tab fields
        gender = request.POST.get('applicable_gender')
        marital_status = request.POST.get('applicable_marital_status')
        departments = request.POST.getlist('applicable_department')  # This can be multiple now
        specific_employees = request.POST.getlist('specific_employees')

        # Entitlement tab fields
        max_days_allowed = request.POST.get('max_days_allowed')
        carry_forward = request.POST.get('carry_forward') == 'True'

        # Restriction tab fields
        count_holidays = request.POST.get('count_holidays')=='True'
        count_weekends = request.POST.get('count_weekends')=='True'

        # Start and End Date fields
        start_from = request.POST.get('start_from')  # Ensure these are datetime formatted
        end_from = request.POST.get('end_from')
        print(count_holidays,"    ","  wekended=",count_weekends)
        # Create the LeaveTypeMaster instance
        leave_type = LeaveTypeMaster.objects.create(
            name=leave_name,
            leavecode=leave_code,
            payable=payable,
            applicable_gender=gender,
            applicable_marital_status=marital_status,
            max_days_allowed=max_days_allowed or 0,
            carry_forward=carry_forward,
            count_holidays=bool(count_holidays),
            count_weekends=bool(count_weekends),
            start_from=start_from,
            end_from=end_from,
        )

        # Handle ManyToMany for departments
        if 'All' not in departments:  # If 'All' is not selected, assign specific departments
            leave_type.applicable_department.set(departments)  # Set the departments (IDs)
        else:
            leave_type.applicable_department.clear()  # No specific department, leave blank (apply to all)

        # Handle specific employees (if applicable)
        if specific_employees:
            # Ensure you're passing only IDs, not the entire objects
            employee_ids = [int(emp_id) for emp_id in specific_employees]  # Convert string IDs to integers
            leave_type.specific_employees.set(employee_ids)  # Set employee IDs directly

            # Optionally initialize leave details for each employee
            employee_objects = EmployeeDetail.objects.filter(id__in=employee_ids)
            for emp_detail in employee_objects:
                initialize_leave_details(emp_detail)

        else:
            # If no specific employees are selected, initialize leave details for all employees
            all_employees = EmployeeDetail.objects.all()
            for emp_detail in all_employees:
                initialize_leave_details(emp_detail)

        messages.success(request, "Leave type added successfully!")
        return redirect('leave_type_panel')

    # GET request - render form
    departments = DepartmentMaster.objects.all()
    employees = emp_registers.objects.filter(job_status=1)

    return render(request, 'add_leave_type.html', {
        'departments': departments,
        'employees': employees
    })


# def update_timesheet(request,user_id):
#     if request.method == 'POST':
#         user_id = request.session.get('user_id')  # Your session user ID
#
#         pname_id = request.POST.get('pname')
#         task = request.POST.get('task')
#         date = request.POST.get('date')
#         start_time = request.POST.get('start_time')
#         end_time = request.POST.get('end_time')
#         description = request.POST.get('description')
#         attachment = request.FILES.get('attachment')
#
#         if pname_id and task and date and start_time and end_time and description:
#             Timesheet.objects.create(
#                 emp_id_id=user_id,
#                 pname_id=pname_id,
#                 task=task,
#                 date=date,
#                 start_time=start_time,
#                 end_time=end_time,
#                 description=description,
#                 attachment=attachment
#             )
#             return redirect('update_timesheet',user_id=user_id)
#
#     projects = Project.objects.all()
#     return render(request, 'update_timesheet.html', {'projects': projects})


# def previous_week_timesheet:
  #
#   return render(request, 'previous_week_timesheet.html')

def update_timesheet(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday','Saturday']
    emp_id = request.session.get('user_id')

    if request.method == 'POST':
        is_weekly = 'weekly' in request.POST

        if is_weekly:

            # Loop over each day in the week to handle weekly timesheet data
            for day in days:
                date = request.POST.get(f'date_{day}')
                pname = request.POST.get(f'pname_{day}')  # Project ID
                task_id = request.POST.get(f'task_{day}')  # Task ID
                start_time = request.POST.get(f'start_time_{day}')
                end_time = request.POST.get(f'end_time_{day}')
                description = request.POST.get(f'description_{day}')
                attachment = request.FILES.get(f'attachment_{day}')

                # Only store the timesheet entry if the project and task are selected
                if date  and  description:
                    try:
                        task_obj = Task.objects.get(id=task_id)
                        Timesheet.objects.create(
                            emp_id_id=emp_id,
                            pname_id=pname,  # Store project ID
                            task=task_obj.title,
                            date=parse_date(date),
                            start_time=start_time or None,
                            end_time=end_time or None,
                            description=description or '',
                            attachment=attachment if attachment else None
                        )

                    except Task.DoesNotExist:
                        continue  # Skip if task is not found
        else:
            # For single-day entry (not weekly), handle daily timesheet data
            date = request.POST.get('date')
            pname = request.POST.get('pname')  # Project ID
            task_id = request.POST.get('task')  # Task ID
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            description = request.POST.get('description')
            attachment = request.FILES.get('attachment')

            # Ensure both project and task are selected
            if pname and task_id:
                try:
                    task_obj = Task.objects.get(id=task_id)
                    Timesheet.objects.create(
                        emp_id_id=emp_id,
                        pname_id=pname,  # Store project ID
                        task=task_obj.title,
                        date=parse_date(date),
                        start_time=start_time or None,
                        end_time=end_time or None,
                        description=description or '',
                        attachment=attachment if attachment else None
                    )
                except Task.DoesNotExist:
                    pass  # silently skip if task not found

        return redirect('user_timesheet')

    # Retrieve projects and tasks related to the logged-in employee
    projects = Project.objects.filter(
        Q(team_members__emp_id=emp_id) & ~Q(status__status='complete')
    )
    tasks = Task.objects.filter(assigned_to__emp_id=emp_id)

    return render(request, 'update_timesheet.html', {
        'projects': projects,
        'days': days,
        'tasks': tasks
    })
from django.conf import settings
def image_timesheet_record(request,user_id):
    user_name = request.session.get('name')  # Assuming user_id is saved in session
    today = date.today()
    user_id = request.session.get('user_id')
    # Calculate current and previous week
    start_of_week = today - timedelta(days=today.weekday())  # Monday of current week
    end_of_week = start_of_week + timedelta(days=6)
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)

    # Filter timesheets where pname.manager or pname.admin == user_id
    user_name = request.session['name']  # e.g., 'Kapil'

    timesheet = []

    timesheets = Timesheet.objects.filter(
            emp_id=user_id,
            description__isnull=True
        ).values('id', 'emp_id', 'date', 'attachment').order_by('-id')
    emp=emp_registers.objects.get(id=user_id)

    for ts in timesheets:
        if ts['attachment']:
            ts['attachment_url'] = settings.MEDIA_URL + ts['attachment']
        else:
            ts['attachment_url'] = None
    for t in timesheets:

        t['end'] = t['date'] + timedelta(days=5)  # Add 5 days to the start date
        timesheet.append(t)  # Add modified record to the list
    team_timesheet = []
    if emp.position.role != 'Employee':

        team_timesheets = Timesheet.objects.filter(
            Q(pname__manager__startswith=user_name) | Q(pname__admin__startswith=user_name),
            date__range=[start_of_last_week, end_of_week]
        ).values('id', 'emp_id', 'date', 'attachment','upload_on').order_by('-id')

        for ts in team_timesheets:
            if ts['attachment']:
                ts['attachment_url'] = settings.MEDIA_URL + ts['attachment']
            else:
                ts['attachment_url'] = None

        print("h")
        for t in team_timesheets:
            emp=emp_registers.objects.get(id=t['emp_id'])
            print('\n\n\n\na aaaa',t)
            t['name']=emp.name
            team_timesheet.append(t)
        for a in team_timesheets:
            a['end'] = a['date'] + timedelta(days=5)
            team_timesheet.append(a)
    return render(request, 'image_timesheet_record.html', context={'timesheet': timesheet,'team_timesheet':team_timesheet})






def image_timesheet(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')

    if request.method == 'POST':
        attachment = request.FILES.get('attachment')
        start_date = request.POST.get('start_date')

        # Get the project for the user
        projects = Project.objects.filter(
            Q(team_members__emp_id=user_id) & ~Q(status__status='complete')
        ).order_by('-id').first()

        # Check if file is uploaded
        if not attachment:
            messages.error(request, "Please upload a file.")
            return redirect('image_timesheet', user_id=user_id)

        try:
            emp=emp_registers.objects.get(id=user_id)
            # Save the new Timesheet record
            new_attachment = Timesheet.objects.create(
                attachment=attachment,
                date=start_date,
                pname=projects,
                emp_id=emp,
                upload_on=timezone.now().date()
            )
            messages.success(request, "Attachment uploaded successfully!")
            return redirect('image_timesheet_record', user_id=user_id)
        except Exception as e:
            # Log the error and show a message to the user
            print(f"Error: {e}")
            messages.error(request, f"Error: {e}")
            return redirect('image_timesheet', user_id=user_id)

    # Ensure you return a response for the GET request
    return render(request, 'image_timesheet.html')


def team_task_report(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    user_id = request.session.get('user_id')  # get from session
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')
    emp = emp_registers.objects.get(id=user_id)
    # Get tasks assigned to the user
    tasks = Task.objects.filter(
        leader=emp.name  ).order_by('-id')


    context = {
        'tasks': tasks,
        'total_tasks': tasks.count(),
        'user_id': user_id,


    }

    return render(request, 'team_task_report.html', context)




def task_list_view(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    user_id = request.session.get('user_id')  # get from session
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    # Get tasks assigned to the user
    # tasks = Task.objects.filter(emp_id=user_id)
    employee = emp_registers.objects.get(id=user_id)
    emp_name = employee.name

    # Filter tasks where assigned_to.name matches the employee's name
    tasks = Task.objects.filter(assigned_to__emp_id=employee.id).order_by('-id')

    context = {
        'tasks': tasks,
        'total_tasks': tasks.count(),
        'user_id': user_id,
    }

    return render(request, 'task_list.html', context)






def add_task_view(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "User not logged in.", extra_tags='task')
        return redirect('login')

    emp = emp_registers.objects.filter(id=user_id).first()
    if not emp:
        messages.error(request, "Employee not found.", extra_tags="task")
        return redirect('login')

    projects = Project.objects.filter(Q(manager=emp) | Q(admin=emp.name) & ~Q(status__status='complete'))
    members = Member.objects.filter(projects__in=projects).distinct()


    if request.method == "POST":
        project_id = request.POST.get('project')
        title = request.POST.get('title')
        description = request.POST.get('description')
        assigned_to_ids = request.POST.getlist('assigned_to')  # Using getlist for ManyToMany field
        due_date = request.POST.get('due_date')

        #status = request.POST.get('status')
        priority = request.POST.get('priority')
        p = PriorityMaster.objects.get(level=priority)
        if due_date:
            try:
                due_date_obj = date.fromisoformat(due_date)
                if due_date_obj < date.today():
                    messages.error(request, "Due date cannot be before today.", extra_tags='task')
                    return render(request, 'add_task.html', {
                        'projects': projects,
                        'members': members,
                        'user_id': user_id
                    })
            except ValueError:
                messages.error(request, "Invalid due date format.", 'task')
                return render(request, 'add_task.html', {
                    'projects': projects,
                    'members': members,
                    'user_id': user_id
                })
        try:
            project = Project.objects.get(id=project_id)
            assigned_to_members = Member.objects.filter(id__in=assigned_to_ids)  # Fetch members based on selected IDs
            status = StatusMaster.objects.get(id=1)
            task = Task.objects.create(
                emp_id=emp,
                start_date=date.today(),
                project=project,
                title=title,
                description=description,
                status=status,
                priority=p,
                leader=emp.name
            )
            task.assigned_to.set(assigned_to_members)  # Set ManyToMany relationship
            task.due_date = due_date if due_date else None
            task.save()

            messages.success(request, "Task added successfully.", 'task')
            return redirect('team_task_report', user_id=user_id)
        except Exception as e:
            messages.error(request, f"Error: {e}", 'task')

    return render(request, 'add_task.html', {
        'projects': projects,
        'members': members,
        'user_id': user_id
    })
from django.http import JsonResponse
 # Adjust import based on your model names
#
# def get_members(request, project_id):
#
#     try:
#         project = Project.objects.get(id=project_id)
#         members = project.members.all()  # Adjust this to your actual relation
#         data = [{"id": member.id, "name": member.emp_id} for member in members]
#         print('\n\n\n\n\n',data)  # Log members to see if they're correct
#         return JsonResponse(data, safe=False)
#     except Project.DoesNotExist:
#         return JsonResponse([], safe=False)  # Return empty list if project is not found



def get_members(request, project_id):
    # Retrieve the selected project
    project = get_object_or_404(Project, id=project_id)

    # Get all members associated with this project via team_members (ManyToMany)
    team_members = project.team_members.all()  # Assuming 'team_members' is a ManyToManyField in Project

    # Prepare the list of members with their ID and name
    member_list = [{'id': member.id, 'name': member.name} for member in team_members]

    # Return members in JSON format
    return JsonResponse(member_list, safe=False)

from django.utils.timezone import now

def update_task_status_page(request, task_id):
    if 'user_id' not in request.session:
        return redirect('login')
    task = get_object_or_404(Task, id=task_id)
    user_id = request.session.get('user_id')
    emp = get_object_or_404(emp_registers, id=user_id)
    position = emp.position.role.lower()  # RoleMaster FK
    project=Project.objects.get(id=task.project.id)
    # Step 1: Define allowed keys (status keywords like 'pending', 'complete')
    if position == "employee":
        if task.status.status.lower() == 'complete':
            allowed_keys = ['complete']
        else:
            allowed_keys = ['hold', 'inprocess', 'claim_complete', 'pending']
    elif position in ['manager', 'hr']:
        if task.status.status.lower() == 'complete':
            allowed_keys = ['complete']
        else:
            allowed_keys = ['hold', 'inprocess', 'complete', 'pending']
    else:
        allowed_keys = []

    # Step 2: Fetch allowed status options from StatusMaster based on allowed_keys
    status_queryset = StatusMaster.objects.filter(status__in=allowed_keys)
    status_options = [(s.status.lower(), s.status) for s in status_queryset]

    # Step 3: Handle POST request to update status
    if task.status.status.lower() != 'complete':
        if request.method == "POST":
            new_status_value = request.POST.get("status")  # e.g. 'complete'

            if new_status_value in allowed_keys:
                try:
                    new_status_obj = StatusMaster.objects.get(status__iexact=new_status_value)
                    task.status = new_status_obj

                    if new_status_obj.status.lower() == 'complete':
                        task.complete_date = now()

                    task.last_update = now()
                    task.save()
                    messages.success(request, "Task status updated successfully.")
                except StatusMaster.DoesNotExist:
                    messages.error(request, "Selected status is invalid.")

            return redirect("task_list_view", user_id=user_id)


    return render(request, "update_task_status.html", {
        "task": task,
        "status_options": status_options,  # passed as (value, label)
        'project':project
    })


def user_timesheet(request):
    # Check if the user is logged in
    if 'user_id' not in request.session:
        return redirect('login')

    user_id = request.session['user_id']  # Get user ID from session

    # Filter timesheets for the logged-in user, with related project name (pname) and order by most recent
    timesheets = Timesheet.objects.filter(emp_id=user_id).select_related('pname').order_by('-id')

    # Implement pagination
    per_page = request.GET.get('per_page', 10)  # Get number of items per page (default to 10)
    paginator = Paginator(timesheets, per_page)
    page_number = request.GET.get('page')  # Get current page number from the request
    page_obj = paginator.get_page(page_number)  # Get the paginated timesheets for the current page

    # Fetch the first user (employee) from the timesheet list (for display)
    user = timesheets.first().emp_id if timesheets else None

    # Pass paginated timesheets and user data to the template
    return render(request, 'user_timesheet.html', {
        'page_obj': page_obj,  # Pass the paginated page object
        'user': user,
        'timesheets': page_obj.object_list  # Only display the timesheets for the current page
    })

import os
import certifi
os.environ['SSL_CERT_FILE'] = certifi.where()

def reset_password(request):
    step = 'email'  # default step

    # STEP 1: Submit email to receive OTP
    if request.method == 'POST' and 'email' in request.POST:
        email = request.POST.get('email')
        try:
            user = emp_registers.objects.get(email=email)
            otp = str(random.randint(100000, 999999))
            request.session['reset_email'] = email
            request.session['otp'] = otp
            print(f"Sending OTP to {email}...")

            print(f"From: {settings.DEFAULT_FROM_EMAIL}")
            print(f"Recipient: {email}")

            send_mail(
                'Password Reset Request - Your OTP',
                f"""
                Dear User,

                We received a request to reset your password. Please use the One-Time Password (OTP) below to proceed:

                OTP: {otp}

                This OTP is valid for the next 15 minutes. If you did not request a password reset, please ignore this email.

                If you have any issues, please contact our support team.

                Best regards,
                Your Company Team
                """,
                settings.DEFAULT_FROM_EMAIL,  # Use the default sender email from settings
                [email],
                fail_silently=False,
            )
            step = 'otp'
        except emp_registers.DoesNotExist:
            messages.error(request, "Email not found.")
            step = 'email'

    # STEP 2: Submit OTP for verification
    elif request.method == 'POST' and 'otp' in request.POST:
        entered_otp = request.POST.get('otp')
        if entered_otp == request.session.get('otp'):
            step = 'password'
        else:
            messages.error(request, "Invalid OTP.")
            step = 'otp'

    # STEP 3: Submit new password
    elif request.method == 'POST' and 'password' in request.POST:
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            step = 'password'
        else:
            email = request.session.get('reset_email')


            emp_registers.objects.filter(email=email).update(password=make_password(password))

            messages.success(request, "Password changed successfully.")
            # Clear session after reset
            request.session.pop('otp', None)
            request.session.pop('reset_email', None)
            return redirect('login')  # adjust this to your login URL name

    return render(request, 'reset_password.html', {'step': step})


# from django.utils.timezone import now
# from django.forms.models import model_to_dict
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import get_object_or_404, redirect, render
# from django.contrib.auth.hashers import make_password, check_password
# from .models import EmployeeDetail, EmployeeDetailHistory
#
# @login_required
# def update_employee_detail(request, emp_id):
#     employee = get_object_or_404(EmployeeDetail, id=emp_id)
#     emp_register = employee.emp_id  # Related emp_registers object
#
#     if request.method == 'POST':
#         old_data = model_to_dict(employee)
#         updated_fields = []
#
#         # Update EmployeeDetail fields
#         for field in [
#             'phone_number', 'guidance_phone_number', 'address', 'father_guidance_name',
#             'blood_group', 'permanent_address', 'gender', 'marriage_status', 'aadhar_no', 'dob',
#             'passport', 'passport_no', 'tel', 'nationality', 'religion', 'marital_status',
#             'primary_contact_name', 'primary_relationship', 'primary_phone',
#             'secondary_contact_name', 'secondary_relationship', 'secondary_phone',
#             'bank_name', 'bank_account_no', 'ifsc_code', 'pan_no'
#         ]:
#             new_value = request.POST.get(field)
#             old_value = str(getattr(employee, field))
#             if new_value is not None and new_value != old_value:
#                 updated_fields.append(field)
#                 setattr(employee, field, new_value)
#
#         # Handle encrypted password (on emp_registers model)
#         new_password = request.POST.get("password")
#         if new_password and not check_password(new_password, emp_register.password):
#             updated_fields.append("password")
#             old_data["password"] = "Encrypted"
#             emp_register.password = make_password(new_password)
#             emp_register.save()
#
#         if updated_fields:
#             employee.save()
#             new_data = model_to_dict(employee)
#
#             if "password" in updated_fields:
#                 new_data["password"] = "Encrypted"
#
#             EmployeeDetailHistory.objects.create(
#                 employee=employee,
#                 start_date=employee.emp_id.joindate if employee.emp_id.joindate else None,
#                 updated_by=request.user,
#                 changed_fields=", ".join(updated_fields),
#                 previous_data={f: old_data.get(f) for f in updated_fields},
#                 new_data={f: new_data.get(f) for f in updated_fields}
#             )
#
#         return redirect('employee_detail', emp_id=employee.id)
#
#     return render(request, 'employee/edit.html', {'employee': employee})


from django.shortcuts import render, redirect
from django.contrib import messages
from .models import emp_registers, EmployeeDetail, Education, Experience, Document
from django.utils.timezone import now

def update_profile(request, user_id):
    if 'user_id' not in request.session:
        return redirect('login')

    emp = emp_registers.objects.get(id=request.session['user_id'])
    profile, created = EmployeeDetail.objects.get_or_create(emp_id=emp)

    if request.method == 'POST':
        # Basic Fields
        profile.phone_number = request.POST.get('phone_number')
        profile.guidance_phone_number = request.POST.get('guidance_phone_number')
        profile.address = request.POST.get('address')
        profile.father_guidance_name = request.POST.get('father_guidance_name')
        profile.blood_group = request.POST.get('blood_group')
        profile.permanent_address = request.POST.get('permanent_address')
        profile.total_leave = request.POST.get('total_leave') or 0
        profile.balance_leave = request.POST.get('balance_leave') or 0
        profile.used_leave = request.POST.get('used_leave') or 0

        # Passport Info
        profile.passport = request.POST.get('passport')
        profile.passport_no = request.POST.get('passport_no')
        profile.tel = request.POST.get('tel')
        profile.nationality = request.POST.get('nationality')
        profile.religion = request.POST.get('religion')
        profile.marital_status = request.POST.get('marital_status')

        # Emergency Contact
        profile.primary_contact_name = request.POST.get('primary_contact_name')
        profile.primary_relationship = request.POST.get('primary_relationship')
        profile.primary_phone = request.POST.get('primary_phone')
        profile.secondary_contact_name = request.POST.get('secondary_contact_name')
        profile.secondary_relationship = request.POST.get('secondary_relationship')
        profile.secondary_phone = request.POST.get('secondary_phone')

        # Bank Info
        profile.bank_name = request.POST.get('bank_name')
        profile.bank_account_no = request.POST.get('bank_account_no')
        profile.ifsc_code = request.POST.get('ifsc_code')
        profile.pan_no = request.POST.get('pan_no')

        if 'profile_image' in request.FILES:
            profile.profile_pic = request.FILES['profile_image']

        profile.save()

        # Education (create new entries)
        education =Education.objects.filter(emp_id=emp)
       #
        print(request.POST)

        existing_degrees = Education.objects.filter(emp_id=emp).values_list('degree', flat=True)
        count = int(request.POST.get("education_count"))
        print("\n\n\n",count)
        for i in range(count):

            index = i + 1
            degree = request.POST.get(f'degree_{index}')
            s=request.POST.get(f'year_{index}')
            print(i,degree,s,)

            if not degree :
                continue
            if degree in existing_degrees:
                continue  # skip if degree already exists for this employee

            year_str = request.POST.get(f'year_{index}')
            institution = request.POST.get(f'institution_{index}')
            grade = request.POST.get(f'grade_{index}')

            try:
                year = int(year_str)
            except (ValueError, TypeError):
                continue  # skip invalid year
            # skip empty row
            # Education.objects.create(
            #     emp_id=emp,
            #     degree=degree,
            #     institution=request.POST.get(f'institution_{index}'),
            #     year_of_passing=int(s),
            #     grade=request.POST.get(f'grade_{index}')
            # )
            education = Education(
                emp_id=emp,
                degree=degree,
                institution=request.POST.get(f'institution_{index}'),
                year_of_passing=int(s),
                grade=request.POST.get(f'grade_{index}')
            )
            print(education)
            education.save()



        # while True:
        #
        #     if not request.POST.get(f'degree_{i + 1}'):
        #         break
        #     s=request.POST.get(f'year_{i + 1}')
        #     Education.objects.create(
        #         emp_id=emp,
        #         degree=request.POST.get(f'degree_{i + 1}'),
        #         institution=request.POST.get(f'institution_{i + 1}'),
        #         year_of_passing=int(s),
        #         grade=request.POST.get(f'grade_{i + 1}')
        #     )
        #
        #     i += 1

        # Experience (update if exist)
        Experience.objects.filter(emp_id=emp).delete()
        i = 0
        while True:
            if not request.POST.get(f'organization_{i + 1}'):
                break
            Experience.objects.create(
                emp_id=emp,
                organization=request.POST.get(f'organization_{i + 1}'),
                position=request.POST.get(f'position_{i + 1}'),
                from_date=request.POST.get(f'from_date_{i + 1}'),
                to_date=request.POST.get(f'to_date_{i + 1}') or None,
                description=request.POST.get(f'description_{i + 1}', '')
            )
            i += 1

        # Document (update if exist)
        Document.objects.filter(emp_id=emp).delete()
        i = 0
        # while True:
        #     if not request.POST.get(f'document_type_{i + 1}'):
        #         break
        #     doc_file = request.FILES.get(f'document_file_{i + 1}')
        #     Document.objects.create(
        #         emp_id=emp,
        #         document_type=request.POST.get(f'document_type_{i + 1}'),
        #         document_name=request.POST.get(f'document_name_{i + 1}'),
        #         document_file=doc_file
        #     )
        #     i += 1

        messages.success(request, "Profile and related information updated with history.")
        return redirect('update_profile', user_id=user_id)

    educations = Education.objects.filter(emp_id=emp)
    experiences = Experience.objects.filter(emp_id=emp)
    documents = Document.objects.filter(emp_id=emp)
    #history = EmployeeDetail.history.filter(emp_id=emp).order_by('-history_date')     use to see history

    return render(request, 'update_profile.html', {
        'profile': profile,
        'educations': educations,
        'experiences': experiences,
        'documents': documents,
        'employee': emp,
        'now': now()
    })
def delete_education(request, pk):
    try:
        # Adjust this if your education model relates differently to the user



        # Attempt to retrieve the education object
        education = Education.objects.get(pk=pk)
        print("Found education:", education)
        education.delete()
        return JsonResponse({'success': True})
    except Education.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Education not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def delete_experience(request, pk):
    # Ensure the user is logged in
    if request.method == 'POST':
        try:
            # Find the experience by ID and ensure it belongs to the logged-in user
            experience = Experience.objects.get(pk=pk)
            experience.delete()  # Delete the experience entry
            return JsonResponse({'success': True})
        except Experience.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Experience not found or not owned by user'})

    return JsonResponse({'success': False, 'error': 'Invalid request'})

def handbook_record(request, handbook_id):
    handbook = get_object_or_404(Handbook, id=handbook_id)
    employees = emp_registers.objects.filter(job_status=1)  # All active employees

    # Create missing acknowledgment records for this handbook
    for employee in employees:
        Acknowledgment.objects.get_or_create(
            employee=employee,
            handbook=handbook,
            defaults={
                'acknowledgment': 'Not Acknowladge',  # Default to not acknowledged
                'acknowledgment_date': None
            }
        )

    # Now fetch all acknowledgment records
    acknowledgments = Acknowledgment.objects.filter(handbook=handbook).select_related('employee', 'handbook')

    return render(request, 'handbook_record.html', {
        'handbook': handbook,
        'acknowledgments': acknowledgments
    })
from django.shortcuts import render, get_object_or_404
from .models import EmployeeDetail, Education, Experience


def employee_profile(request, emp_id):
    # Get employee detail

    employee = get_object_or_404(EmployeeDetail, emp_id=emp_id)

    # Get related education records
    education_list = Education.objects.filter(emp_id=emp_id)

    # Get related experience records
    experience_list = Experience.objects.filter(emp_id=emp_id)
    #
    # Render template with context
    return render(request, 'employee_profile.html', {
        'employee': employee,
        'education_list': education_list,
        'experience_list': experience_list,
        'emp_id':emp_id
    })
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import localtime
from .models import EmployeeDetail

def view_profile_history(request, emp_id):
    # Get the current employee object
    employee = get_object_or_404(EmployeeDetail, emp_id=emp_id)

    # Get historical records in ascending order of history date
    history_records = EmployeeDetail.history.filter(emp_id=emp_id).order_by('history_date')

    field_history_map = {}  # Track change history for each field

    # Go through each historical record
    for i, record in enumerate(history_records):
        current_data = record.__dict__

        for field, new_value in current_data.items():
            if field.startswith('_') or field in ['id', 'history_id', 'history_user_id',
                                                  'history_type', 'history_change_reason',
                                                  'history_date', 'emp_id_id']:
                continue

            # Get previous value for the field
            last_record = field_history_map.get(field, [])

            if last_record:
                prev_value = last_record[-1]['new']
                if prev_value != new_value:
                    # Value changed, so append new history entry
                    last_record.append({
                        'field': field,
                        'old': prev_value,
                        'new': new_value,
                        'created_date': last_record[-1]['created_date'],  # same as last change date
                        'change_date': localtime(record.history_date).strftime('%Y-%m-%d %H:%M:%S')
                    })
                    field_history_map[field] = last_record
            else:
                # First time value seen → create initial record
                field_history_map[field] = [{
                    'field': field,
                    'old': '',
                    'new': new_value,
                    'created_date': localtime(record.history_date).strftime('%Y-%m-%d %H:%M:%S'),
                    'change_date': 'Not changed'
                }]

    # Flatten the dict into a list
    changes = []
    for field, field_changes in field_history_map.items():
        for i in range(len(field_changes)):
            if i < len(field_changes) - 1:
                # Set created_date as the current, and change_date as the next's created_date
                field_changes[i]['change_date'] = field_changes[i + 1]['created_date']
            changes.append(field_changes[i])

    return render(request, 'view_profile_history.html', {
        'employee': employee,
        'changes': sorted(changes, key=lambda x: x['created_date']),  # sort by created date
    })


from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Handbook, Acknowledgment
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.shortcuts import render
from .models import Handbook, Acknowledgment


def handbook_list(request):
    if request.method == 'POST':
        # Handle file upload for a new handbook
        document = request.FILES.get('document')
        document_name=request.POST.get('document_name')

        if document:
            # Calculate logical start date based on the current date or any other logic
            start_date = now().date()

            # Deactivate all old handbooks
            Handbook.objects.all().update(active_status=False)
            current_handbook= Handbook.objects.get().order_by('-id').first()
            current_handbook.end_date=start_date

            # Get the last active handbook and set its end_date to the start_date of the new one
            last_handbook = Handbook.objects.filter(active_status=True).order_by('-start_date').first()

            if last_handbook:
                # Set the end date of the last active handbook to the start date of the new one
                last_handbook.end_date = start_date
                last_handbook.save()

            # Create a new handbook entry
            # Example logic for the end date (30 days later)

            # Create the new handbook and set it as active
            new_handbook = Handbook.objects.create(
                document=document,
                start_date=start_date,

                active_status=True  # New handbook is active
            )

            return JsonResponse({'success': True, 'message': 'Handbook added successfully'})

        return JsonResponse({'success': False, 'message': 'Failed to add handbook'}, status=400)

    # GET request to display handbooks
    handbooks = Handbook.objects.all().order_by('-id')


    data = []
    for h in handbooks:
        handbook = get_object_or_404(Handbook, id=h.id)

        # Get all employees
        employees = emp_registers.objects.filter(job_status=1)

        # Ensure acknowledgment exists for all employees

        for emp in employees:
            ack, created = Acknowledgment.objects.get_or_create(
                handbook=handbook,
                employee=emp,
                defaults={
                    'acknowledgment_date': None,
                    'acknowledgment': 'Not Acknowledge',
                    'status': 'active'
                }
            )

            data.append({
                'employee': str(emp),
                'acknowledgment_date': ack.acknowledgment_date.strftime(
                    '%Y-%m-%d') if ack.acknowledgment_date else 'Not yet',
                'agreement': ack.acknowledgment
            })
            context = {
                'handbooks': handbooks,'acknowledgments':data
            }

    return render(request, 'handbook_list.html', context)
from django.http import JsonResponse

def acknowledgments_for_handbook(request, handbook_id):
    handbook = get_object_or_404(Handbook, id=handbook_id)
    data=[]
    # Get all employees
    employees = emp_registers.objects.filter(job_status=1)

    # Ensure acknowledgment exists for all employees

    for emp in employees:
        ack, created = Acknowledgment.objects.get_or_create(
            handbook=handbook,
            employee=emp,
            defaults={
                'acknowledgment_date': None,
                'acknowledgment': 'Not Acknowledge',
                'status': 'active'
            }
        )

        data.append({
            'employee': str(emp),
            'acknowledgment_date': ack.acknowledgment_date.strftime(
                '%Y-%m-%d') if ack.acknowledgment_date else 'Not yet',
            'agreement': ack.acknowledgment
        })

    return JsonResponse({'acknowledgments': data})


from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from .models import Handbook, Acknowledgment, emp_registers

def handbook_view(request, user_id):
    employee = get_object_or_404(emp_registers, pk=user_id)

    # Fetch the latest active handbook
    handbook = Handbook.objects.filter(active_status='True').order_by('-start_date').first()

    if not handbook:
        return render(request, "employee/handbook_view.html", {
            "error": "No active handbook available."
        })

    acknowledgment, created = Acknowledgment.objects.get_or_create(
        employee=employee,
        handbook=handbook,
    )

    if request.method == "POST":
        action = request.POST.get("acknowledgment")

        if action in ['agree', 'disagree']:
            acknowledgment.acknowledgment = action
            acknowledgment.acknowledgment_date = timezone.now().date()

            acknowledgment.save()

            return redirect('handbook',user_id=user_id)  # Replace with your success view

    return render(request, "handbook.html", {
        "handbook": handbook,
        "acknowledgment": acknowledgment
    })



def acknowledge_handbook(request, handbook_id):
    if request.method == 'POST':
        # Get the user's acknowledgment choice
        ack_choice = request.POST.get('ack')

        # Get the relevant handbook
        handbook = Handbook.objects.get(id=handbook_id)

        # Update or create the acknowledgment record
        ack, created = Acknowledgment.objects.get_or_create(
            handbook=handbook,
            user=request.user,
        )
        ack.acknowledged = True if ack_choice == 'agree' else False
        ack.acknowledged_at = timezone.now()
        ack.save()

        return JsonResponse({'status': 'saved'})

    return JsonResponse({'status': 'error'}, status=400)


def manage_leave_department_role(request):
    # Fetch data from the database for the dropdown options
    departments = DepartmentMaster.objects.all()
    roles = RoleMaster.objects.all()
    leave_types = LeaveTypeMaster.objects.all()
   #  d leave_types = LeaveTypeMaster.objects.all()
   # epartments = DepartmentMaster.objects.all()
   #  roles = (RoleMaster.objects.all())


    # Handle form submission for adding leave type
    if request.method == 'POST':
        if 'name' in request.POST:  # This means the leave type form was submitted
            leave_name = request.POST.get('name')
            applicable_gender = request.POST.get('applicable_gender')
            applicable_marital_status = request.POST.get('applicable_marital_status')
            applicable_department = request.POST.get('applicable_department')
            specific_employees = request.POST.getlist('specific_employees')
            count_holidays = 'count_holidays' in request.POST
            count_weekends = 'count_weekends' in request.POST

            # Save the leave type to the database
            LeaveTypeMaster.objects.create(
                name=leave_name,
                applicable_gender=applicable_gender,
                applicable_marital_status=applicable_marital_status,
                applicable_department_id=applicable_department,
                count_holidays=count_holidays,
                count_weekends=count_weekends
            )

        elif 'department_name' in request.POST:  # This means the department form was submitted
            department_name = request.POST.get('department_name')

            # Save the department to the database
            DepartmentMaster.objects.create(name=department_name)

        elif 'role_name' in request.POST:  # This means the role form was submitted
            role_name = request.POST.get('role_name')

            # Save the role to the database
            RoleMaster.objects.create(name=role_name)

    # Pass data to the template
    context = {
        'departments': departments,
        'roles': roles,
        'leave_types': leave_types
    }

    return render(request, 'manage_leave_department_role.html', context)


def get_existing_data(request, category):
    """
    AJAX endpoint to fetch existing data (leave types, roles, departments)
    based on the category selected.
    """
    if category == 'leave':
        data = [leave.name for leave in LeaveTypeMaster.objects.all()]
    elif category == 'role':
        data = [role.name for role in RoleMaster.objects.all()]
    elif category == 'department':
        data = [department.name for department in DepartmentMaster.objects.all()]
    else:
        data = []

    return JsonResponse({'data': data})



def leave_type_panel(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            leave_id = data.get('id')
            leave_status = data.get('status', True)

            leave = LeaveTypeMaster.objects.get(id=leave_id)
            leave.leave_status = leave_status
            leave.save()

            employees = EmployeeDetail.objects.all()
            # for emp in employees:
            #     initialize_leave_details(emp)

            return JsonResponse({'success': True})

        except LeaveTypeMaster.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave type not found'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    # GET request: paginate leave masters
    page_size = request.GET.get('page_size', '10')
    leave_masters = LeaveTypeMaster.objects.all()
    leave_records = LeaveRecord.objects.all()

    paginator = Paginator(leave_masters, page_size)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'leave_type_panel.html', {
        'leave_masters': page_obj,
        'leave_records': leave_records,
        'page_obj': page_obj,
    })

def project_detail_view(request, pk):
    if 'user_id' not in request.session:
        return redirect('login')
    # Step 1: Fetch project and user details
    project = get_object_or_404(Project, id=pk)
    user_id = request.session.get('user_id')
    emp = get_object_or_404(emp_registers, id=user_id)
    position = emp.position.role.lower()  # Get user's role (e.g., 'employee', 'manager', 'hr')

    # Step 2: Define allowed status options based on the user's role and current project status
    if position == "employee":
        if project.status.status.lower() == 'complete':
            allowed_keys = ['complete']
        else:
            allowed_keys = ['hold', 'inprocess', 'claim_complete', 'pending']
    elif position in ['manager', 'hr']:
        if project.status.status.lower() == 'complete':
            allowed_keys = ['complete']
        else:
            allowed_keys = ['hold', 'inprocess', 'complete', 'pending']
    else:
        allowed_keys = []  # No allowed statuses for other roles

    # Step 3: Fetch the allowed status options from StatusMaster based on the allowed_keys
    status_queryset = StatusMaster.objects.filter(status__in=allowed_keys)
    status_options = [(s.status.lower(), s.status) for s in status_queryset]  # (value, label)

    # Step 4: Handle POST request to update the project's status
    if project.status.status.lower() != 'complete':  # Prevent changing the status if it's already 'complete'
        if request.method == "POST":
            new_status_value = request.POST.get("status")  # The status selected by the user (e.g., 'complete')

            if new_status_value in allowed_keys:
                try:
                    # Step 5: Fetch the StatusMaster object corresponding to the selected status
                    new_status_obj = StatusMaster.objects.get(status__iexact=new_status_value)
                    project.status = new_status_obj  # Update the project's status

                    # If the status is 'complete', set the complete date
                    if new_status_obj.status.lower() == 'complete':
                        project.complete_date = now()

                    project.last_update = now()  # Update the last updated timestamp
                    project.save()  # Save the project with the new status
                    messages.success(request, "Project status updated successfully.")
                except StatusMaster.DoesNotExist:
                    messages.error(request, "Selected status is invalid.")

            return redirect("project_detail", pk=pk)

    # Step 6: Render the project detail page with the status options
    context = {
        'project': project,
        'status_options': status_options,  # Passed as (value, label) pairs
        'user_id': request.session['user_id'],
    }
    return render(request, 'project_detail_view.html', context)


def project_edit_view(request, project_id):
    # Fetch the project using the provided project_id
    project = get_object_or_404(Project, id=project_id)

    # Fetch necessary data for the project edit form
    rate_status_list = RateStatusMaster.objects.all()
    managers = emp_registers.objects.filter(position__role__iexact='Manager')
    priority_list = PriorityMaster.objects.all()
    employee_members = emp_registers.objects.filter(position__role__iexact='Employee')

    selected_team_members = project.team_members.values_list('id', flat=True)

    if request.method == "POST":
        try:
            # Extract form data
            pname = request.POST.get("pname")
            client = request.POST.get("client")
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")
            rate_status_id = request.POST.get("rate_status")
            rate = request.POST.get("rate")  # Already a float field, no need to cast
            manager = request.POST.get("manager")
            priority_id = request.POST.get("priority")
            team_members = request.POST.getlist("team_members")
            description = request.POST.get("description")

            # Convert the start date to a date object for validation
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

            # Validation

            m = emp_registers.objects.get(id=manager)  # Fetch manager by ID
            # Update project fields
            project.pname = pname
            project.client = client
            project.start_date = start_date_obj
            project.end_date = end_date_obj
            project.rate_status_id = rate_status_id
            project.rate = float(rate)  # Ensure rate is saved as float
            project.manager = m.name
            project.priority_id = priority_id
            project.description = description
            project.last_update = now()


            # Update team members - Ensure team_member_names are integers
            # Convert list of team_member IDs (from POST data) to integers
            team_member_ids = [int(member) for member in team_members]

            # Convert emp_registers to Member instances
            team_members_list = []
            for emp_id in team_member_ids:
                employee = emp_registers.objects.filter(id=emp_id).first()
                if employee:
                    member, _ = Member.objects.get_or_create(
                        emp_id=employee,  # Assuming ForeignKey to emp_registers
                        defaults={
                            'name': employee.name,
                            'email': employee.email
                        }
                    )
                    team_members_list.append(member)

            # Set the converted members to the project
            project.team_members.set(team_members_list)
            project.save()
            user_id=request.session.user_id
            messages.success(request, "Project details updated successfully.")

            messages.success(request, "Project details updated successfully.")
            return redirect('project_detail', pk=user_id)

        except Exception as e:
            messages.error(request, f"Error updating project: {e}")

    # Render the project edit page with the relevant context
    return render(request, 'project_edit.html', {
        'project': project,
        'rate_status_list': rate_status_list,
        'managers': managers,
        'priority_list': priority_list,
        'employee_members': employee_members,
        'selected_team_members': selected_team_members,
    })




def team_timesheet_record(request):
    user_name = request.session.get('name')  # Assuming user_id is saved in session
    today = date.today()
    user_id=request.session.get('user_id')
    # Calculate current and previous week
    start_of_week = today - timedelta(days=today.weekday())  # Monday of current week
    end_of_week = start_of_week + timedelta(days=6)
    start_of_last_week = start_of_week - timedelta(days=7)
    end_of_last_week = start_of_week - timedelta(days=1)



    # Filter timesheets where pname.manager or pname.admin == user_id
    user_name = request.session['name']  # e.g., 'Kapil'

    timesheets = Timesheet.objects.filter(
        Q(pname__manager__startswith=user_name) | Q(pname__admin__startswith=user_name),
        date__range=[start_of_last_week, end_of_week]
    ).select_related('emp_id', 'pname')
    for timesheet in timesheets:
        if timesheet.start_time and timesheet.end_time:
            # Combine date and time to calculate the difference
            start = datetime.combine(today, timesheet.start_time)
            end = datetime.combine(today, timesheet.end_time)
            duration = end - start
            timesheet.duration = duration
        else:
            timesheet.duration = None
    context = {
        'timesheets': timesheets,
    }
    return render(request, 'team_timesheet_record.html',   {'timesheets': timesheets})



def get_project_members(request, project_id):
    try:
        project = Project.objects.get(id=project_id)
        members = project.team_members.all()
        data = [{'id': m.id, 'name': m.name} for m in members]
        return JsonResponse(data, safe=False)
    except Project.DoesNotExist:
        return JsonResponse([], safe=False)




def leave_type_detail_view(request, leave_type_id):
    leave_type = get_object_or_404(LeaveTypeMaster, id=leave_type_id)
    leave_records = LeaveRecord.objects.filter(
        leave_type=leave_type
    ).select_related('emp_id').order_by('-id')

    # Default limit is now 10
    limit = request.GET.get('limit', '10')
    paginator = Paginator(leave_records, int(limit))
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if request.method == 'POST':
        # If delete action is triggered for the leave type
        if 'delete_leave_type' in request.POST:
            leave_type.delete()
            return redirect('leave_type_panel')  # Redirect to the leave type panel or a different page after deletion
    return render(request, 'leave_type_detail.html', {
        'leave_type': leave_type,
        'page_obj': page_obj,
        'limit': limit,
    })



from django.shortcuts import render, redirect, get_object_or_404
from datetime import datetime, timedelta
from django.utils import timezone
from .models import emp_registers, Resignation, ResignationStatusMaster, ResignStatusAction

from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import datetime, timedelta
from .models import emp_registers, Resignation, ResignationStatusMaster, ResignStatusAction
from datetime import datetime, timedelta
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from .models import emp_registers, Resignation, ResignationStatusMaster, ResignStatusAction

def resignation_form(request, user_id):
    employee = get_object_or_404(emp_registers, id=user_id)

    # Get all resignations for this employee (latest first)
    resignation_qs = Resignation.objects.filter(employee=employee).order_by('-id')

    if not resignation_qs.exists():
        # No resignation found, allow to submit new one
        if request.method == 'POST':
            resign_date_str = request.POST.get('resign_date')
            reason = request.POST.get('reason')

            def to_bool(value):
                return value == 'yes'

            selected_elsewhere = to_bool(request.POST.get('selected_elsewhere'))
            bond_over = to_bool(request.POST.get('bond_over'))
            advance_salary = to_bool(request.POST.get('advance_salary'))
            dues_pending = to_bool(request.POST.get('dues_pending'))

            resign_date = datetime.strptime(resign_date_str, "%Y-%m-%d").date()
            last_date = resign_date + timedelta(days=90)

            # Status: Apply
            default_status = ResignationStatusMaster.objects.get(status_name="Apply")

            # Create Resignation
            resignation = Resignation.objects.create(
                employee=employee,
                resign_date=resign_date,
                last_date=last_date,
                reason=reason,
                selected_elsewhere=selected_elsewhere,
                bond_over=bond_over,
                advance_salary=advance_salary,
                dues_pending=dues_pending,
                resign_status=default_status
            )

            # Log the status in ResignStatusAction
            ResignStatusAction.objects.create(
                resignation=resignation,
                action=default_status.status_name,  # Pass the name, not object
                action_by=employee,
                action_date=timezone.now()
            )

            return redirect('send_exit_email', user_id=user_id)

        return render(request, 'exit_management.html', {'employee': employee})

    else:
        latest_resignation = resignation_qs.first()
        current_status_name = latest_resignation.resign_status.status_name

        if current_status_name == "Apply":
            return redirect('handle_incomplete_resignation',user_id=user_id)
        elif current_status_name == 'Submit':
            return redirect('resignation_activity', user_id=user_id)
        elif current_status_name == 'Withdraw':
            # Allow employee to reapply if resignation status is 'Withdraw'
            if request.method == 'POST':
                # Reapply the resignation process
                resign_date_str = request.POST.get('resign_date')
                reason = request.POST.get('reason')

                resign_date = datetime.strptime(resign_date_str, "%Y-%m-%d").date()
                last_date = resign_date + timedelta(days=90)

                # Status: Apply
                default_status = ResignationStatusMaster.objects.get(status_name="Apply")

                # Create new Resignation (reapply)
                resignation = Resignation.objects.create(
                    employee=employee,
                    resign_date=resign_date,
                    last_date=last_date,
                    reason=reason,
                    selected_elsewhere=latest_resignation.selected_elsewhere,
                    bond_over=latest_resignation.bond_over,
                    advance_salary=latest_resignation.advance_salary,
                    dues_pending=latest_resignation.dues_pending,
                    resign_status=default_status
                )

                # Log the status in ResignStatusAction
                ResignStatusAction.objects.create(
                    resignation=resignation,
                    action=default_status.status_name,
                    action_by=employee,
                    action_date=timezone.now()
                )

                return redirect('handle_incomplete_resignation',user_id=user_id)

            return render(request, 'exit_management.html', {
                'employee': employee,
                'resignation': latest_resignation
            })
        else:
            return render(request, 'resignation_activity.html', {
                'employee': employee,
                'resignation': latest_resignation
            })


def handle_incomplete_resignation(request,user_id):
    employee = get_object_or_404(emp_registers, id=user_id)
    try:
        resignation = Resignation.objects.filter(employee=employee).latest('id')
    except Resignation.DoesNotExist:
        messages.warning(request, "No resignation record found.")
        return redirect('d2',id=user_id)
    if request.method == 'POST':
        if 'complete' in request.POST:
            # Render the 'send_exit_email.html' page with context
            return redirect('send_exit_email', user_id=user_id)
        elif 'delete' in request.POST:
            ResignStatusAction.objects.filter(resignation=resignation).delete()
            resignation.delete()
            return redirect('exit_management', user_id=user_id)
    return render(request, 'incomplete_warning.html')

def get_tasks(request):
    project_id = request.GET.get('project_id')
    tasks = Task.objects.filter(project_id=project_id)
    task_data = [{'id': task.id, 'title': task.title} for task in tasks]
    return JsonResponse({'tasks': task_data})

from django.core.mail import EmailMultiAlternatives
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt  # optional for testing
from django.conf import settings

from django.core.mail import EmailMultiAlternatives
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from .models import SentEmail, emp_registers  # Ensure you import your model
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import emp_registers, Resignation, ResignStatusAction, SentEmail, ResignationStatusMaster
from django.core.mail import EmailMultiAlternatives

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from datetime import datetime
from .models import emp_registers, Resignation, ResignationStatusMaster, ResignStatusAction, SentEmail
# from django.core.mail import EmailMultiAlternatives  # Uncomment to use email sending

def send_exit_email(request, user_id):
    employee = get_object_or_404(emp_registers, id=user_id)

    # Check if the resignation status is already "Submit"
    try:
        resignation = Resignation.objects.filter(employee=employee).latest('id')
        submit_status = ResignationStatusMaster.objects.get(status_name="Submit")

        if resignation.resign_status == submit_status:
            return redirect('resignation_activity', user_id=user_id)
    except Resignation.DoesNotExist:
        resignation = None  # No resignation found, continue normally
    except ResignationStatusMaster.DoesNotExist:
        messages.error(request, "Submit status not found in master table.")
        return redirect('error_page')  # Use your own error page or message

    if request.method == 'POST':
        print('Inside send mail POST')

        from_email = request.POST.get('from')
        to_email = request.POST.get('to')
        cc = request.POST.get('cc', '')
        bcc = request.POST.get('bcc', '')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        to_list = [to_email]
        cc_list = [email.strip() for email in cc.split(',') if email.strip()]
        bcc_list = [email.strip() for email in bcc.split(',') if email.strip()]

        try:
            # Optional: Uncomment this to actually send the email
            # email_msg = EmailMultiAlternatives(
            #     subject=subject,
            #     body=message,
            #     from_email=from_email,
            #     to=to_list,
            #     cc=cc_list,
            #     bcc=bcc_list,
            # )
            # email_msg.attach_alternative(message, "text/html")
            # email_msg.send()

            # Save the email to DB
            SentEmail.objects.create(
                employee=employee,
                recipient_email=to_email,
                subject=subject,
                message_body=message
            )

            # Update status to Submit
            resignation.resign_status = submit_status
            resignation.save()

            # Log the status change
            ResignStatusAction.objects.create(
                resignation=resignation,
                action=submit_status,
                action_by=employee
            )

            messages.success(request, "Email sent, resignation marked as 'Submit', and status logged.")
            print('\n\n\n\n vwv')
            return redirect('resignation_activity', user_id=user_id)

        except Exception as e:
            messages.error(request, f"Failed to send email or update status: {e}")
            return redirect('send_exit_email', user_id=user_id)

    return render(request, 'send_exit_email.html', {'employee': employee})

from django.shortcuts import render
from .models import Resignation, emp_registers, ResignStatusAction, DepartmentMaster, DesignationMaster

def resignation_list(request):
    all_resignations = Resignation.objects.select_related('employee', 'resign_status').order_by('-id')
    resignation_data_section1 = []
    resignation_data_section2 = []

    user_position = request.session.get('postion')  # e.g., 'manager' or 'hr'

    for resignation in all_resignations:
        emp = emp_registers.objects.filter(id=resignation.employee.id).first()
        if not emp:
            continue

        department = emp.department.name if emp.department else "N/A"
        designation = emp.designation.designation_name if emp.designation else "N/A"
        try:
            latest_action = ResignStatusAction.objects.filter(resignation=resignation).order_by('-id').first()
        except ResignStatusAction.DoesNotExist:
            latest_action = None
        m=[4, 5, 6, 7, 8, 3]
        h=[3, 4, 5, 7, 8]
        data = {
            'emp_id': emp.id,
            'employee_name': emp.name,
            'resign_date': resignation.resign_date,
            'status': resignation.resign_status.status_name,
            'status_id': resignation.resign_status.id,  # For badge color
            'department': department,
            'designation': designation,
            'latest_action': latest_action.action if latest_action else 'N/A',
            'reason': resignation.reason,
            'm': m,
            'h': h,


        }

        # Section 1 filter (single row depending on role and status id)
        if (user_position == 'Manager' and resignation.resign_status.id == 2) or \
           (user_position == 'HR' and resignation.resign_status.id == 4):
            resignation_data_section1.append(data)

        # Section 2 filter (remaining statuses)
        elif resignation.resign_status.id in [ 3, 4, 5, 6, 7, 8]:
            resignation_data_section2.append(data)

    departments = DepartmentMaster.objects.all()
    designations = DesignationMaster.objects.all()

    return render(request, 'resignation_list.html', {
        'resignation_data_section1': resignation_data_section1,
        'resignation_data_section2': resignation_data_section2,
        'departments': departments,
        'designations': designations
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .audit_logger import log_audit_action # Import your new logging utility
from .models import LeaveRecord, Project, emp_registers # Import models as needed by your views

@login_required
def approve_leave_view(request, leave_id):
    leave_record = get_object_or_404(LeaveRecord, pk=leave_id)
    if request.method == 'POST':
        # ... logic to approve the leave ...
        leave_record.approval_status = LeaveRecord.objects.get(status='Approved') # Assuming you fetch the Approved status
        leave_record.approved_by = request.user.emp_registers.name # Assuming user.emp_registers gives the employee instance
        leave_record.save() # This save will trigger the post_save signal for LeaveRecord

        log_audit_action(request.user.username,
                         f"approved leave application (ID: {leave_id}) for {leave_record.emp_id.name}")
        return redirect('leave_list')
    return render(request, 'approve_leave_form.html', {'leave_record': leave_record})

@login_required
def view_all_projects(request):
    projects = Project.objects.all()
    log_audit_action(request.user.username, "opened all projects list")
    return render(request, 'projects/project_list.html', {'projects': projects})

@login_required
def generate_custom_report(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type', 'unknown')
        # ... logic to generate the report ...
        log_audit_action(request.user.username, f"generated a custom '{report_type}' report")
        return redirect('report_download_page')
    return render(request, 'reports/generate_report_form.html')

# Example for an admin action not directly tied to a model save/delete
# such as deactivating a user (which might not delete the emp_registers entry)


# You'll do this for all other views where specific, non-CRUD actions happen.
from django.http import HttpResponse
from .utils.audit import log_user_action

def sample_view(request):
    if request.user.is_authenticated:
        log_user_action(request.user.id, "Accessed sample view")
    return HttpResponse("Audit logged.")
# your_app/views.py


from datetime import date, timedelta
from django.shortcuts import render
from django.db.models import Q
from calendar import monthrange
import calendar
from django.utils import timezone
# No Paginator import needed for client-side pagination here

# Import your models
from .models import Holiday, LeaveRecord, emp_registers, LeaveStatusMaster
import calendar
from datetime import date, timedelta
from django.utils import timezone
from calendar import monthrange
from django.db.models import Q


# Assuming these are your models
# from .models import emp_registers, Holiday, LeaveRecord
import calendar
from datetime import date
from calendar import monthrange
from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone  # Make sure to import timezone


# Assuming your models are imported like this:
# from .models import emp_registers, Holiday, LeaveRecord
from django.shortcuts import render
from django.utils import timezone
from datetime import date
from calendar import monthrange
from collections import defaultdict
from django.db.models import Q
from .models import emp_registers, Holiday, LeaveRecord
import calendar
from datetime import date
from calendar import monthrange
from collections import defaultdict
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Q
from .models import LeaveRecord, Holiday, emp_registers
import calendar

def attendance_view(request):
    try:
        selected_year = int(request.GET.get('year', timezone.localdate().year))
        selected_month = int(request.GET.get('month', timezone.localdate().month))
        assert 1 <= selected_month <= 12
    except (ValueError, AssertionError):
        selected_year = timezone.localdate().year
        selected_month = timezone.localdate().month

    today = timezone.localdate()

    # --- Employee Search Filter ---
    search_query = request.GET.get('search')
    if search_query:
        employees_qs = emp_registers.objects.filter(
            Q(name__icontains=search_query) | Q(id__icontains=search_query)
        ).order_by('id')
    else:
        employees_qs = emp_registers.objects.filter(job_status=1).order_by('name')

    # --- Fetch Holidays ---
    holidays_query = Holiday.objects.filter(
        date__year=selected_year,
        date__month=selected_month
    ).values_list('date', 'name')
    holidays_dict = {h_date: h_name for h_date, h_name in holidays_query}

    # --- Fetch Leaves ---
    start_of_month = date(selected_year, selected_month, 1)
    end_of_month = date(selected_year, selected_month, monthrange(selected_year, selected_month)[1])
    leave_records_qs = LeaveRecord.objects.filter(
        Q(start_date__lte=end_of_month) & Q(end_date__gte=start_of_month),
        approval_status__status='Approved'
    ).select_related('emp_id')

    employee_leaves = defaultdict(list)
    for leave in leave_records_qs:
        employee_leaves[leave.emp_id].append(leave)

    attendance_data = []
    num_days_in_month = monthrange(selected_year, selected_month)[1]
    days_in_month_header_range = list(range(1, num_days_in_month + 1))

    # --- Calculate 2nd and 3rd Saturdays ---
    second_saturday = third_saturday = None
    saturday_count = 0
    for day_num in range(1, num_days_in_month + 1):
        temp_date = date(selected_year, selected_month, day_num)
        if temp_date.weekday() == 5:
            saturday_count += 1
            if saturday_count == 2:
                second_saturday = temp_date
            elif saturday_count == 3:
                third_saturday = temp_date
                break

    # --- Build Attendance Rows ---
    for employee in employees_qs:
        employee_attendance_row = {
            'id': employee.id,
            'name': employee.name,
            'employee_id': employee.id,
            'days_data': []
        }

        for day_num in days_in_month_header_range:
            current_date_obj = date(selected_year, selected_month, day_num)
            day_of_week = current_date_obj.weekday()

            status = '-'
            reason = ''
            cell_class = ''

            # 1. Future Date
            if current_date_obj > today:
                status = '-'
                reason = 'Future Date'
                cell_class = 'future-date'

            else:
                # 2. Check Leave FIRST (higher priority)
                leave_found = False
                for leave in employee_leaves.get(employee, []):
                    if leave.start_date <= current_date_obj <= leave.end_date:
                        status = 'L'
                        reason = leave.reason or 'On Leave'
                        cell_class = 'leave-day'
                        leave_found = True
                        break

                if not leave_found:
                    # 3. Check Sunday
                    if day_of_week == 6:
                        status = 'W'
                        reason = 'Sunday'
                        cell_class = 'weekend-day'

                    # 4. Check 2nd/3rd Saturday
                    elif day_of_week == 5 and current_date_obj in [second_saturday, third_saturday]:
                        status = 'W'
                        reason = 'Saturday'
                        cell_class = 'weekend-day'

                    # 5. Check Holiday
                    elif current_date_obj in holidays_dict:
                        status = 'H'
                        reason = holidays_dict[current_date_obj]
                        cell_class = 'holiday-day'

                    # 6. Present
                    else:
                        status = 'P'
                        reason = 'Present'
                        cell_class = 'present-day'

            # 7. Today Highlight
            if current_date_obj == today:
                cell_class = f"{cell_class} today-date".strip()

            employee_attendance_row['days_data'].append({
                'day_num': day_num,
                'status': status,
                'reason': reason,
                'class': cell_class
            })

        attendance_data.append(employee_attendance_row)

    # --- Dropdown Context ---
    month_options = [
        {'value': m, 'name': calendar.month_name[m], 'selected': (m == selected_month)}
        for m in range(1, 13)
    ]
    current_year_py = timezone.localdate().year
    year_options_list = list(range(current_year_py - 2, current_year_py + 3))

    context = {
        'selected_year': selected_year,
        'selected_month': selected_month,
        'num_days_in_month': num_days_in_month,
        'employees_attendance': attendance_data,
        'today_date': today,
        'current_day': today.day,
        'current_month': today.month,
        'current_year': today.year,
        'year_options': year_options_list,
        'month_options': month_options,
        'days_in_month_header_range': days_in_month_header_range,
    }

    return render(request, 'attendance.html', context)


from django.http import Http404

def resignation_activity(request, user_id):
    employee = get_object_or_404(emp_registers, id=user_id)
    resignation = Resignation.objects.filter(employee=employee).order_by('-resign_date').first()

    if not resignation:
        raise Http404("No resignation found for this employee.")

    # Get or create the checklist for this resignation.
    checklist, created = ActionChecklist.objects.get_or_create(resignation=resignation)

    status_actions = resignation.status_actions.all().order_by('action_date')
    email = SentEmail.objects.filter(employee_id=user_id).order_by('-sent_at').first()

    # Get the position of the currently logged-in user from the session.
    position = request.session.get('postion')
    # Get the emp_registers instance of the user who is logged in and performing actions.
    current_user_emp = get_object_or_404(emp_registers, id=request.session.get('user_id'))

    action_label = None # This variable will store the description for ResignStatusAction

    if request.method == 'POST':
        action = request.POST.get('action')

        # --- Handle Checklist Form Submission ---
        if 'checklist_action' in request.POST and request.POST['checklist_action'] == 'save_checklist':
            checklist.status_ongoing_projects = 'ongoing_projects' in request.POST
            checklist.outstanding_tasks = 'outstanding_tasks' in request.POST
            checklist.important_contacts = 'important_contacts' in request.POST
            checklist.update_passwords = 'update_passwords' in request.POST
            checklist.revoke_access = 'revoke_access' in request.POST
            checklist.remove_from_payroll = 'remove_from_payroll' in request.POST
            checklist.update_employee_directory = 'update_employee_directory' in request.POST
            checklist.official_resignation_letter = 'official_resignation_letter' in request.POST
            checklist.last_paycheck_arrangements = 'last_paycheck_arrangements' in request.POST
            checklist.nda = 'nda' in request.POST
            checklist.laptop_and_charger = 'laptop_and_charger' in request.POST
            checklist.mouse = 'mouse' in request.POST
            checklist.exit_interview_conducted = 'exit_interview_conducted' in request.POST
            checklist.send_announcement = 'send_announcement' in request.POST
            checklist.give_farewell_party = 'give_farewell_party' in request.POST

            checklist.save()
            messages.success(request, "Exit Checklist updated successfully!")
            return redirect('resignation_activity', user_id=user_id)

        # --- Handle Last Working Date Update (HR specific) ---
        elif action == 'update_last_date' and position == 'HR':
            new_last_date = request.POST.get('last_date')
            if new_last_date:
                resignation.last_date = new_last_date
                resignation.save()
                messages.success(request, "Last working date updated.")
            else:
                messages.error(request, "Please select a valid date to update.")
            return redirect('resignation_activity', user_id=user_id)

        # --- Handle Manager Actions ---
        elif position == 'Manager' and resignation.resign_status.id == 2:
            if action == 'approve':
                resignation.resign_status_id = 4
                messages.success(request, "Resignation approved by Manager.")
                action_label = 'Manager Approved'
            elif action == 'reject':
                resignation.resign_status_id = 5
                messages.success(request, "Resignation rejected by Manager.")
                action_label = 'Rejected by Manager'

        # --- Handle Employee Actions ---
        elif position == 'Employee' and resignation.resign_status.id not in [7, 8, 5]:
            if action == 'withdraw':
                resignation.resign_status_id = 3
                messages.success(request, "Resignation withdrawn successfully.")
                action_label = 'Withdrawn'

        # --- Handle HR Approval/Rejection Actions ---
        elif position == 'HR' and resignation.resign_status.id == 4:
            if action == 'approve_hr':
                resignation.resign_status_id = 6
                messages.success(request, "Resignation approved by HR.")
                action_label = 'HR Approved'
            elif action == 'reject_hr':
                resignation.resign_status_id = 8
                messages.success(request, "Resignation rejected by HR.")
                action_label = 'Rejected by HR'

        # --- Handle HR Finalize Action ---
        elif position == 'HR' and action == 'finish':
            if resignation.resign_status.id == 6:
                finalized_resignation_status = get_object_or_404(ResignationStatusMaster, id=7)
                # CHANGE: Set employee's job_status to ID 2 (e.g., 'Resigned' or 'Left')
                finalized_job_status = get_object_or_404(JobStatusMaster, id=2)

                resignation.resign_status = finalized_resignation_status
                resignation.save()

                employee.job_status = finalized_job_status # Update employee's job status
                employee.save()

                ResignStatusAction.objects.create(
                    resignation=resignation,
                    action='Finalized',
                    action_by=current_user_emp,
                    action_date=timezone.now()
                )
                messages.success(request, "Resignation finalized and employee job status updated to 'Left'.")
                return redirect('resignation_activity', user_id=user_id)
            else:
                messages.error(request, "Resignation cannot be finalized in its current status. It must be HR Approved.")
                return redirect('resignation_activity', user_id=user_id)

        # --- Log Action for Manager/Employee/HR Status Changes ---
        if action_label:
            resignation.save()

            ResignStatusAction.objects.create(
                resignation=resignation,
                action=action_label,
                action_by=current_user_emp,
                action_date=timezone.now()
            )
            return redirect('resignation_activity', user_id=user_id)

    # Context to pass to the template
    context = {
        'employee': employee,
        'resignation': resignation,
        'status_actions': status_actions,
        'checklist': checklist,
        'email': email,
        'position': position,
    }
    return render(request, 'resignation_activity.html', context)


from .models import TodoTask

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime
from .models import toda_task
 # change yourapp to your app name
def todo_view(request):
    # your code to render todo.html
    return render(request, 'todo.html')

def toda_tasks_api(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        user = emp_registers.objects.get(pk=user_id)
    except emp_registers.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)

    if request.method == 'GET':
        tasks = toda_task.objects.filter(user=user).order_by('datetime')
        tasks_list = [{
            'id': t.id,
            'desc': t.desc,
            'badge': t.badge,
            'datetime': t.datetime.isoformat(),
        } for t in tasks]
        return JsonResponse({'tasks': tasks_list})

    elif request.method == 'POST':
        data = json.loads(request.body)
        desc = data.get('desc')
        badge = data.get('badge', 'success')
        dt_str = data.get('datetime')

        if not desc or not dt_str:
            return JsonResponse({'error': 'Missing fields'}, status=400)

        dt = parse_datetime(dt_str)
        if not dt:
            return JsonResponse({'error': 'Invalid datetime'}, status=400)

        task = toda_task.objects.create(user=user, desc=desc, badge=badge, datetime=dt)
        return JsonResponse({'id': task.id})

    elif request.method == 'PUT':
        data = json.loads(request.body)
        task_id = data.get('id')
        dt_str = data.get('datetime')
        badge = data.get('badge')
        desc = data.get('desc')

        try:
            task = toda_task.objects.get(id=task_id, user=user)
        except toda_task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

        if dt_str:
            dt = parse_datetime(dt_str)
            if not dt:
                return JsonResponse({'error': 'Invalid datetime'}, status=400)
            task.datetime = dt
        if badge:
            task.badge = badge
        if desc:
            task.desc = desc

        task.save()
        return JsonResponse({'success': True})

    elif request.method == 'DELETE':
        data = json.loads(request.body)
        task_id = data.get('id')
        try:
            task = toda_task.objects.get(id=task_id, user=user)
            task.delete()
            return JsonResponse({'success': True})
        except toda_task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

    return JsonResponse({'error': 'Method not allowed'}, status=405)
def delete_task(request, id):
    TodoTask.objects.get(id=id).delete()
    return redirect('todo')

def change_badge(request, id):
    task = TodoTask.objects.get(id=id)
    cycle = ['success', 'danger', 'secondary']
    task.badge = cycle[(cycle.index(task.badge) + 1) % 3]
    task.save()
    return redirect('todo')


import csv
from io import TextIOWrapper
from django.shortcuts import render
import pandas as pd
from django.contrib import messages

from django.shortcuts import render
from django.contrib import messages
from decimal import Decimal
# from .models import Payslip
import pandas as pd
from io import TextIOWrapper
from decimal import Decimal
from io import TextIOWrapper
import pandas as pd
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import render
 # Make sure this import matches your project structure

def payslip_from_csv(request):
    payslip_data = []

    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a valid CSV file.')
            return render(request, 'payslip_from_csv.html', {'records': payslip_data})

        try:
            file_data = TextIOWrapper(csv_file.file, encoding='utf-8')
            lines = file_data.readlines()
            file_data.seek(0)

            # Detect header
            headers_line = lines[0].strip()
            headers = headers_line.split(',')

            # Remove any duplicate header rows
            data_lines = [line for line in lines if line.strip().split(',') != headers]

            # Convert cleaned data lines back to a file-like object
            from io import StringIO
            cleaned_file = StringIO(''.join(data_lines))

            # Read into DataFrame
            df = pd.read_csv(cleaned_file)

            # Clean column names
            df.columns = df.columns.str.strip().str.replace(' ', '_').str.replace('\t', '')

            # Numeric columns to ensure proper dtype
            numeric_columns = [
                'SALARY_BASIC', 'SALARY_HRA', 'SALARY_DA', 'TOTAL_SALARY',
                'GROSS_BASIC', 'GROSS_HRA', 'GROSS_DA', 'CONVENCE_ALLOWNCE',
                'SPECIAL_ALLOWNCES', 'Project_Incentive', 'Variable_Pay',
                'GROSS_TOTAL', 'ESI', 'PF', 'Salary_Advance', 'Negative_Leave', 'TDS',
                'Total_Deductions', 'NET_SALARY'
            ]
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

            # Calculate Total_Deductions
            deduction_components = ['ESI', 'PF', 'Salary_Advance', 'Negative_Leave', 'TDS']
            if all(col in df.columns for col in deduction_components):
                df['Total_Deductions'] = df[deduction_components].sum(axis=1)
            elif 'Total_Deductions' not in df.columns:
                df['Total_Deductions'] = 0

            # Calculate NET_SALARY
            if 'SALARY_BASIC' in df.columns and 'SALARY_HRA' in df.columns and 'Allowance' in df.columns:
                df['NET_SALARY'] = (df['SALARY_BASIC'] + df['SALARY_HRA'] + df['Allowance']) - df['Total_Deductions']
            else:
                df['NET_SALARY'] = 0

            # Set defaults
            if 'Month' not in df.columns:
                df['Month'] = 'June 2025'
            if 'Department' not in df.columns:
                df['Department'] = 'Not Specified'
            if 'Allowance' not in df.columns:
                df['Allowance'] = 0

            # Create DataFrame for display and DB insert
            temp_df = pd.DataFrame()
            temp_df['Employee_Name'] = df['Employee_Name'] if 'Employee_Name' in df.columns else 'N/A'
            temp_df['Employee_ID'] = df['Employee_Email'] if 'Employee_Email' in df.columns else 'N/A'
            temp_df['Month'] = df['Month']
            temp_df['Department'] = df['Department']
            temp_df['Basic'] = df['SALARY_BASIC'] if 'SALARY_BASIC' in df.columns else 0
            temp_df['HRA'] = df['SALARY_HRA'] if 'SALARY_HRA' in df.columns else 0
            temp_df['Allowance'] = df['Allowance']
            temp_df['Deductions'] = df['Total_Deductions']
            temp_df['Net_Salary'] = df['NET_SALARY']

            payslip_data = temp_df.to_dict(orient='records')

            # Save to DB
            inserted = 0
            updated = 0
            for row in payslip_data:
                try:
                    obj, created = Payslip.objects.update_or_create(
                        employee_id=row['Employee_ID'],
                        month=row['Month'],
                        defaults={
                            'employee_name': row['Employee_Name'],
                            'department': row['Department'],
                            'basic': Decimal(row['Basic']),
                            'hra': Decimal(row['HRA']),
                            'allowance': Decimal(row['Allowance']),
                            'deductions': Decimal(row['Deductions']),
                            'net_salary': Decimal(row['Net_Salary']),
                        }
                    )
                    if created:
                        inserted += 1
                    else:
                        updated += 1
                except Exception as db_error:
                    messages.warning(request, f"Error saving record for {row.get('Employee_ID', 'Unknown')}: {db_error}")

            messages.success(request, f'Successfully uploaded {inserted} new and updated {updated} payslip records.')

        except Exception as e:
            messages.error(request, f'An error occurred while processing the CSV file: {e}')

    return render(request, 'payslip_from_csv.html', {'records': payslip_data})



def employee_salary_history(request, emp_id):
    # Filter all payslips of the employee by ID
    payslips = Payslip.objects.filter(employee_id=emp_id).order_by('-uploaded_at')

    context = {
        'payslips': payslips,
        'emp_id': emp_id,
    }
    return render(request, 'employee_salary_history.html', context)


from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
# from .models import Payslip

from django.core.paginator import Paginator
from django.shortcuts import render
# from .models import Payslip

def payslip_list(request):
    # Get search query
    search_query = request.GET.get('search', '')
    month_filter = request.GET.get('month', '')

    # Filter the payslips based on search query and month
    payslips = Payslip.objects.all()
    if search_query:
        payslips = payslips.filter(employee_name__icontains=search_query)
    if month_filter:
        payslips = payslips.filter(month=month_filter)

    # Handle rows per page (10, 20, or 'All')
    rows_per_page = request.GET.get('rows_per_page', 10)
    if rows_per_page == 'all':
        paginator = Paginator(payslips, payslips.count())  # Show all records
    else:
        paginator = Paginator(payslips, int(rows_per_page))  # Show 10 or 20 records

    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Calculate the current page number and total pages
    total_pages = paginator.num_pages
    current_page = page_obj.number

    return render(request, 'payslip_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'month_filter': month_filter,
        'rows_per_page': rows_per_page,
        'current_page': current_page,
        'total_pages': total_pages
    })


import csv
from io import BytesIO
import pandas as pd
from django.http import HttpResponse
# from .models import Payslip
# import xlsxwriter

def export_payslips_csv(request):
    # Get payslip data, with optional filters for month and search
    payslips = Payslip.objects.all()
    month_filter = request.GET.get('month', None)
    if month_filter:
        payslips = payslips.filter(month=month_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        payslips = payslips.filter(
            Q(employee_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )

    # Create the CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="payslips.csv"'

    writer = csv.writer(response)
    writer.writerow(['Employee Name', 'Employee ID', 'Month', 'Department', 'Basic', 'HRA', 'Allowance', 'Deductions',
                     'Net Salary'])

    for payslip in payslips:
        writer.writerow([
            payslip.employee_name,
            payslip.employee_id,
            payslip.month,
            payslip.department,
            payslip.basic,
            payslip.hra,
            payslip.allowance,
            payslip.deductions,
            payslip.net_salary
        ])

    return response


def export_payslips_excel(request):
    # Get payslip data, with optional filters for month and search
    payslips = Payslip.objects.all()
    month_filter = request.GET.get('month', None)
    if month_filter:
        payslips = payslips.filter(month=month_filter)

    search_query = request.GET.get('search', '')
    if search_query:
        payslips = payslips.filter(
            Q(employee_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        )

    # Create Excel response using Pandas
    df = pd.DataFrame(list(payslips.values(
        'employee_name', 'employee_id', 'month', 'department', 'basic', 'hra',
        'allowance', 'deductions', 'net_salary'
    )))

    # Save the dataframe to an Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Payslips')
        writer.save()

    output.seek(0)
    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="payslips.xlsx"'

    return response


import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from .models import toda_task
from datetime import datetime


@require_http_methods(["GET", "POST"])
@csrf_exempt
def toda_tasks_api(request):
    if request.method == "GET":
        tasks = toda_task.objects.select_related('user').all()
        tasks_list = []
        for t in tasks:
            tasks_list.append({
                "id": t.id,
                "desc": t.desc,
                "datetime": t.datetime.isoformat(),
                "badge": t.badge,
                "user": t.user.name if t.user else None,
            })
        return JsonResponse({"tasks": tasks_list})

    elif request.method == "POST":
        data = json.loads(request.body)
        desc = data.get("desc")
        badge = data.get("badge", "success")
        datetime_str = data.get("datetime")
        dt = datetime.fromisoformat(datetime_str)

        # For demo, assign a user, or you can get user from request.user if auth enabled
        # Example: user = request.user.emp_registers
        # Here, let's assume user id 1 exists (change as per your app)

        user = emp_registers.objects.first()  # Replace this to assign proper user

        task = toda_task.objects.create(user=user, desc=desc, badge=badge, datetime=dt)
        return JsonResponse({"id": task.id, "desc": desc, "badge": badge, "datetime": datetime_str})


@require_http_methods(["PUT"])
@csrf_exempt
def update_task_datetime(request):
    data = json.loads(request.body)
    task_id = data.get("id")
    datetime_str = data.get("datetime")
    dt = datetime.fromisoformat(datetime_str)

    try:
        task = toda_task.objects.get(id=task_id)
        task.datetime = dt
        task.save()
        return JsonResponse({"success": True})
    except toda_task.DoesNotExist:
        return JsonResponse({"error": "Task not found"}, status=404)


import json
import requests
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .models import HRPolicy # Import the HRPolicy model

# ... (Any existing imports and views you have in staff/views.py) ...

# Replace with your actual Gemini API Key if running locally.
# If running in a Canvas environment, leave this as an empty string;
# the key is automatically provided during the fetch call.
GEMINI_API_KEY = ""

def tokenize_and_clean(text):
    """
    Helper function to tokenize and clean a string for keyword extraction.
    Removes punctuation and converts to lowercase.
    """
    if not isinstance(text, str):
        return []
    import re
    return [
        word for word in re.sub(r'[.,/#!$%^&*;:{}=\-_`~()]', '', text.lower()).split()
        if len(word) > 2 # Filter out very short words
    ]

def retrieve_relevant_content(query):
    """
    Retrieves relevant HR policies from the database based on the query,
    using a keyword-based scoring mechanism.
    """
    query_keywords = tokenize_and_clean(query)
    scored_documents = []

    # Fetch all policies from the database
    policies = HRPolicy.objects.all()

    for policy in policies:
        score = 0
        doc_title_keywords = tokenize_and_clean(policy.title)
        doc_content_keywords = tokenize_and_clean(policy.content)

        # Score based on keyword presence in title (higher weight)
        for q_keyword in query_keywords:
            if q_keyword in doc_title_keywords:
                score += 2
            if q_keyword in doc_content_keywords:
                score += 1

        if score > 0: # Only consider documents with at least one match
            scored_documents.append({'doc': policy, 'score': score})

    # Sort documents by score in descending order
    scored_documents.sort(key=lambda x: x['score'], reverse=True)

    # Select the top 2 most relevant documents
    top_relevant_docs = scored_documents[:2]

    relevant_text = ""
    if top_relevant_docs:
        for item in top_relevant_docs:
            relevant_text += f"**From \"{item['doc'].title}\":**\n{item['doc'].content}\n\n"
    return relevant_text

@csrf_exempt # IMPORTANT: For API endpoints called via POST without Django's template rendering.
             # NOT RECOMMENDED FOR PRODUCTION. See notes below for CSRF.
def chatbot_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_query = data.get('query', '')

            if not user_query:
                return JsonResponse({'error': 'Query parameter is missing'}, status=400)

            retrieved_content = retrieve_relevant_content(user_query)

            # Construct the prompt for the LLM
            if retrieved_content:
                prompt = f"""
                You are an HR assistant for a company. Your task is to answer employee questions ONLY based on the provided HR policy context.
                If the answer is not found in the context, politely state that you cannot provide the information from the given policies and suggest contacting HR directly.
                Try to interpret the user's intent even if the query is not phrased exactly as in the policy, as long as the answer is derivable from the provided context.

                **HR Policy Context:**
                {retrieved_content}

                **Employee Question:**
                {user_query}

                Please provide a concise and helpful answer based on the context.
                """
            else:
                prompt = f"""
                You are an HR assistant. An employee has asked the following question: "{user_query}".
                I was unable to find specific relevant policy documents for this query within my knowledge base.
                Please politely inform the employee that you cannot find the answer in the available policies and suggest they contact the HR department directly for assistance.
                """

            chat_history_for_api = [{"role": "user", "parts": [{"text": prompt}]}]
            payload = {"contents": chat_history_for_api}

            headers = {'Content-Type': 'application/json'}
            api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            if GEMINI_API_KEY: # Only append key if it's set (for local dev)
                api_url += f"?key={GEMINI_API_KEY}"

            api_response = requests.post(api_url, headers=headers, data=json.dumps(payload))
            api_response.raise_for_status() # Raise an exception for HTTP errors (e.g., 4xx or 5xx)

            result = api_response.json()

            bot_text = "Sorry, I could not generate a response."
            if result.get('candidates') and len(result['candidates']) > 0 and \
               result['candidates'][0].get('content') and \
               result['candidates'][0]['content'].get('parts') and \
               len(result['candidates'][0]['content']['parts']) > 0:
                bot_text = result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"Unexpected API response structure: {result}") # For debugging

            return JsonResponse({'response': bot_text})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON in request body'}, status=400)
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return JsonResponse({'error': f'Failed to connect to AI service: {e}'}, status=500)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return JsonResponse({'error': f'An internal server error occurred: {e}'}, status=500)
    return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

def chatbot_page(request):
    """
    Renders the main chatbot HTML page.
    """
    return render(request, 'chatbot.html') # Note the 'staff/' directory