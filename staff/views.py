from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import *
from datetime import datetime,date
from django.contrib import messages
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
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import LeaveTypeMaster, LeaveRecord
import json

def d1(request,id):
    user = get_object_or_404(emp_registers, id=id)
    return render(request, '1.html', {'user': user})

def d2(request,id):
    user = get_object_or_404(emp_registers, id=id)
    return render(request, '2.html', {'user': user})




def home_view(request):
    return render(request, 'home.html')





def update_employee(request, id):
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
                messages.error(request, 'All fields are required!')
                return redirect('update_employee', id=id)

            # 2. Validate Password (if entered)
            if password:
                if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*]', password):
                    messages.error(request, 'Password must be at least 8 characters, include an uppercase letter, a number, and a special character.')
                    return redirect('update_employee', id=id)

            # 3. Check join date logic
            try:
                if joindate > datetime.today().date():
                    messages.error(request, 'Joining date cannot be in the future.')
                    return redirect('update_employee', id=id)

                if joindate < datetime(2025, 1, 1).date():
                    messages.error(request, 'Joining date cannot be before January 1, 2025.')
                    return redirect('update_employee', id=id)
            except ValueError:
                messages.error(request, 'Invalid join date format.')
                return redirect('update_employee', id=id)

            # 4. Save the form data
            form.save()
            messages.success(request, "Employee details updated successfully!")
            return redirect('employee_list')
        else:
            messages.error(request, "Failed to update. Please correct the errors in the form.")
    else:
        form = EmployeeForm(instance=employee)

    return render(request, 'update_employee.html', {'form': form, 'employee': employee})


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me', False)

        if not email or not password:
            messages.error(request, 'Email and password are required.')
            return render(request, 'login.html')

        try:
            user = emp_registers.objects.get(email=email)
            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['name'] = user.name
                request.session['postion'] = user.position.role

                # request.session['img']=user.profile_pic.url

                if remember_me:
                    request.session.set_expiry(604800)  # 1 week
                else:
                    request.session.set_expiry(0)

                if user.position.role  == 'HR':
                    return redirect('d1', id=user.id)
                else:
                    return redirect('d2', id=user.id)
            else:
                messages.error(request, 'Invalid email or password.')
        except emp_registers.DoesNotExist:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')



#




def employee_registration(request, id):
    # Get the current employee by ID
    user = emp_registers.objects.filter(id=id).first()

    # If the user is not found, redirect to an error page
    if not user:
        messages.error(request, "User not found.")
        return redirect('some_error_page')  # Redirect to an error page or a safe place.

    # Fetch all positions (from RoleMaster) and departments (from DepartmentMaster)
    positions = RoleMaster.objects.all()
    departments = DepartmentMaster.objects.all()

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

            # Call initializer only if eligible
            if eligible:
                initialize_leave_details(employee_detail)

            # Success message
            messages.success(request, 'Employee registration successful!')
            return redirect('employee_registration', id=id)  # Redirect to the same page

        else:
            # Error message if form is not valid
            messages.error(request, 'Please correct the errors below.')

    else:
        # If it's a GET request, create an empty form
        form = EmployeeForm()

    # Render the template with the form, user, and the position/department choices
    return render(request, 'employee registration.html', {
        'form': form,
        'user': user,
        'id': id,
        'positions': positions,  # Pass positions to the template
        'departments': departments  # Pass departments to the template
    })




def change_password(request):
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



def update_profile(request,user_id):
    emp = emp_registers.objects.get(id=request.session['user_id'])  # Get logged-in user
    profile, created = EmployeeDetail.objects.get_or_create(emp_id=emp)  # Get or create profile

    if request.method == 'POST':
        profile.phone_number = request.POST.get('phone_number')
        profile.guidance_phone_number = request.POST.get('guidance_phone_number')
        profile.address = request.POST.get('address')
        profile.father_guidance_name = request.POST.get('father_guidance_name')
        profile.blood_group = request.POST.get('blood_group')
        profile.permanent_address = request.POST.get('permanent_address')
        profile.total_leave = request.POST.get('total_leave') or 0
        profile.balance_leave = request.POST.get('balance_leave') or 0
        profile.used_leave = request.POST.get('used_leave') or 0
        profile.job_status = request.POST.get('job_status')

        # Passport
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

        # Education & Experience
        profile.education_info = request.POST.get('education_info')
        profile.experience = request.POST.get('experience')

        # Image Upload
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('update_profile')

    return render(request, 'update_profile.html', {'profile': profile})






def project(request, user_id):
    projects = Project.objects.prefetch_related('team_members__emp_id').all().order_by('-id')
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




from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import date
from django.utils.dateparse import parse_date
from .models import emp_registers, Project, RateStatusMaster, PriorityMaster, StatusMaster, Member

def add_project_view(request, user_id):
    user_id = request.session.get('user_id')
    try:
        emp = emp_registers.objects.get(id=user_id)
        admin_name = emp.name
    except emp_registers.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect('login')

    managers = emp_registers.objects.filter(position__role__iexact='Manager')
    employee_members = emp_registers.objects.filter(position__role__iexact='Employee')
    rate_status_list = RateStatusMaster.objects.all()
    priority_list = PriorityMaster.objects.all()
    status_list = StatusMaster.objects.all()

    if request.method == "POST":
        pname = request.POST.get('pname')
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        rate = request.POST.get('rate')
        rate_status = request.POST.get('rate_status')
        priority = request.POST.get('priority')
        description = request.POST.get('description')
        client = request.POST.get('client')
        manager_emp_id = request.POST.get('manager')
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
        manager = None
        if manager_emp_id:
            try:
                manager = emp_registers.objects.get(id=manager_emp_id)
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
            rate=rate,
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



def employee_list(request):
    # Get filters from request
    position_filter = request.GET.get('position', '')
    department_filter = request.GET.get('department', '')
    page_size = int(request.GET.get('page_size', 10))  # Default to 10
    page_number = request.GET.get('page', 1)

    # Base queryset
    employees = emp_registers.objects.all()

    # Filter by role
    if position_filter:
        employees = employees.filter(position__role=position_filter)

    # Filter by department name or ID
    if department_filter:
        employees = employees.filter(department__id=department_filter)

    # Apply pagination
    paginator = Paginator(employees, page_size)
    page_obj = paginator.get_page(page_number)

    # Fetch for dropdowns
    department_choices = DepartmentMaster.objects.all()

    return render(request, 'employee_list.html', {
        'employees': page_obj,  # paginated queryset
        'department_choices': department_choices,
    })


def leave_record_view(request,user_id):
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

    return render(request, 'leave_record.html', {'leave_record': leave_records})



import random
def set_page_size_preference(request):
    if request.method == "POST":
        page_size = request.POST.get("page_size")
        if page_size:
            request.session["preferred_page_size"] = page_size
            return JsonResponse({"success": True})
    return JsonResponse({"success": False})




def delete_employee(request, id):
    employee = get_object_or_404(emp_registers, id=id)
    employee.delete()
    messages.success(request, "emp_registers deleted successfully!")
    return redirect('employee_list')





def apply_leave(request, user_id):
    try:
        employee = EmployeeDetail.objects.get(emp_id=user_id)
    except EmployeeDetail.DoesNotExist:
        messages.error(request, "Employee details not found.")
        return redirect('login')

    # Fetch only necessary fields
    leave_types = LeaveTypeMaster.objects.filter(leave_status=True).values(
        'id', 'name', 'applicable_gender', 'payable', 'applicable_marital_status',
        'applicable_department', 'leavecode', 'leave_status',
        'count_holidays', 'count_weekends'
    )

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type_id = request.POST.get('leave_type')
        reason = request.POST.get('reason')

        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        leave_type = LeaveTypeMaster.objects.get(id=leave_type_id)

        # Half-day logic
        half_day_data = request.POST.getlist('half_day[]')
        half_day_dict = {}
        for entry in half_day_data:
            if entry:
                date, half = entry.rsplit('-', 1)
                half_day_dict[date] = half

        # Calculate leave days
        leave_days = 0.0
        current_date = start_date
        while current_date <= end_date:
            # half_day_entry = HalfdayMaster.objects.filter(
            #     date=current_date,
            #     emp_id=employee  # EmployeeDetail object
            # ).select_related('half_day_type').first()
            str_date = str(current_date)
            leave_days += 0.5 if str_date in half_day_dict else 1.0
            current_date += timedelta(days=1)

        # Check leave balance
        if employee.balance_leave >= leave_days:
            emp_instance = employee.emp_id  # This is from ForeignKey in EmployeeDetail

            # Default pending status (optional — better to fetch from LeaveStatusMaster if needed)
            pending_status = LeaveStatusMaster.objects.filter(status__iexact='pending').first()

            leave_application = LeaveRecord(
                emp_id=emp_instance,
                start_date=start_date,
                end_date=end_date,
                no_of_days=leave_days,
                leave_type=leave_type,
                reason=reason,
                approval_status=pending_status
            )
            leave_application.save()

            messages.success(request, "Leave application submitted successfully!")
            return redirect('apply_leave', user_id=user_id)
        else:
            messages.error(request, "Insufficient leave balance.")

    return render(request, 'apply_leave.html', {
        'employee': employee,
        'balance_leave': employee.balance_leave,
        'used_leave': employee.used_leave,
        'leave_types': leave_types
    })






def update_total_leaves():

    current_year = date.today().year
    employees = emp_registers.objects.all()  # Fetch all employees from emp_registers

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
    # Ensure the user is logged in
    # if 'user_id' not in request.session:
    #     return redirect('/login/')

    # Get logged-in user details
    username = request.session.get('name')
    today = now().date()

    # Fetch leave records for the logged-in employee
    leave_records = LeaveRecord.objects.filter(emp_id=user_id).order_by('-id').values(
        'id', 'created_at', 'start_date', 'end_date', 'no_of_days', 'reason', 'approval_status', 'emp_id','approved_by','approve_reason'
    )
    emp=emp_registers.objects.filter(id=user_id)
    # Prepare data to be passed to the template
    leave_data = []

    for leave in leave_records:
        try:
            emp_data = emp_registers.objects.get(id=leave['emp_id'])
            report_to = emp_data.reportto if emp_data.reportto else 'Not Assigned'
            leave_data.append({
                's_no': len(leave_data) + 1,  # Serial number
                'name':emp_data.name,
                'current_date': leave['created_at'],
                'start_date': leave['start_date'],
                'end_date': leave['end_date'],
                'no_of_leaves': leave['no_of_days'],
                'reason': leave['reason'],
                'approval_status': leave['approval_status'],
                'report_to': report_to,
                'leave_id': leave['id'],
                'approved_by':leave['approved_by'],
                'approve_reason':leave['approve_reason']
            })
        except emp_registers.DoesNotExist:
            continue  # Skip if employee data not found

    # Render the dashboard template with the leave data
    return render(request, 'leave_dashboard.html', {
        'leave_data': leave_data,
        'username': username,
        'today': today,'emp':emp
    })






def update_leave_status(request, user_id):
    approver = emp_registers.objects.get(id=user_id)  # Get the approver (manager, HR, etc.)

    if request.method == "POST":
        leave_id = request.POST.get("leave_id")
        action = request.POST.get("action")  # Expected: Approved, Rejected, Withdrawn
        reason = request.POST.get('reason', '')  # Get reason from form (if any)

        leave_record = get_object_or_404(LeaveRecord, id=leave_id)
        employee = EmployeeDetail.objects.get(emp_id=leave_record.emp_id.id)  # Get the employee who applied for leave

        status_obj = LeaveStatusMaster.objects.filter(status=action).first()
        if not status_obj:
            return JsonResponse({"error": f"'{action}' status not configured."}, status=500)

        previous_status = leave_record.approval_status.status if leave_record.approval_status else ""

        # Withdraw logic
        if action == "Withdrawn":
            if now().date() > leave_record.start_date:
                return JsonResponse({"error": "Cannot withdraw, start date has passed."}, status=400)

            if previous_status == "Approved":
                # If the leave was approved before, update the balance and used leave for the employee who applied
                employee.balance_leave += leave_record.no_of_days
                employee.used_leave -= leave_record.no_of_days
                employee.save()

        # Approve logic
        elif action == "Approved":
            # If leave is already approved, update balance and used leave for the employee who applied
            if previous_status == "Approved":
                employee.balance_leave -= leave_record.no_of_days
                employee.used_leave += leave_record.no_of_days
                employee.save()

            leave_record.approval_status = status_obj
            leave_record.approved_by = approver.name
            employee.balance_leave -= leave_record.no_of_days
            employee.used_leave += leave_record.no_of_days
            employee.save()

        # Reject logic
        elif action == "Rejected":
            if previous_status == "Approved":
                # If previously approved, revert balance and used leave for the employee who applied
                employee.balance_leave += leave_record.no_of_days
                employee.used_leave -= leave_record.no_of_days
                employee.save()

            leave_record.approval_status = status_obj
            leave_record.approved_by = approver.name
            leave_record.approve_reason = reason
        # Final update for all status changes
        leave_record.approval_status = status_obj
        leave_record.approved_by = approver.name
        leave_record.save()

        return JsonResponse({
            "status": leave_record.approval_status.status,
            "approved_by": leave_record.approved_by
        })

    return JsonResponse({"error": "Invalid request"}, status=400)


from django.contrib import messages
from .models import LeaveTypeMaster, DepartmentMaster, emp_registers

def initialize_leave_details(emp_detail):
    leave_data = {}

    # Get all active leave types
    leave_types = LeaveTypeMaster.objects.filter(leave_status=True)

    for leave_type in leave_types:
        code = leave_type.leavecode or leave_type.name[:3].upper()
        total = leave_type.max_days_allowed or 0
        leave_data[code] = {
            "used": 0,
            "balance": total,
            "total": total
        }

    # Set leave_details
    emp_detail.leave_details = leave_data
    emp_detail.save()

def add_leave_type(request):
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
        count_holidays = request.POST.get('count_holidays') == 'True'
        count_weekends = request.POST.get('count_weekends') == 'True'

        # Start and End Date fields
        start_from = request.POST.get('start_from')  # Ensure these are datetime formatted
        end_from = request.POST.get('end_from')

        # Create the LeaveTypeMaster instance
        leave_type = LeaveTypeMaster.objects.create(
            name=leave_name,
            leavecode=leave_code,
            payable=payable,
            applicable_gender=gender,
            applicable_marital_status=marital_status,
            max_days_allowed=max_days_allowed or 0,
            carry_forward=carry_forward,
            count_holidays=count_holidays,
            count_weekends=count_weekends,
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
            leave_type.specific_employees.set(specific_employees)



        # Initialize leave for all or specific employees


        if specific_employees:
            for emp_id in specific_employees:
                emp_detail = EmployeeDetail.objects.filter(emp_id_id=emp_id).first()
                if emp_detail:
                    initialize_leave_details(emp_detail)
        else:
            for emp_detail in EmployeeDetail.objects.all():
                initialize_leave_details(emp_detail)

        messages.success(request, "Leave type added successfully!")


        messages.success(request, "Leave type added successfully!")
        return redirect('leave_type_panel')

    # GET request - render form
    departments = DepartmentMaster.objects.all()
    employees = emp_registers.objects.all()
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




def update_timesheet(request, user_id):
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
    emp_id = request.session.get('user_id')

    if request.method == 'POST':
        is_weekly = 'weekly' in request.POST

        if is_weekly:
            print("adedfsgfghfdhhgdghgfhghhdfhghhgh")
            for day in days:
                date = request.POST.get(f'date_{day}')
                pname = request.POST.get(f'pname_{day}')
                task = request.POST.get(f'task_{day}')
                start_time = request.POST.get(f'start_time_{day}')
                end_time = request.POST.get(f'end_time_{day}')
                description = request.POST.get(f'description_{day}')
                attachment = request.FILES.get(f'attachment_{day}')

                if date and pname and task:
                    Timesheet.objects.create(
                        emp_id_id=emp_id,
                        pname_id=pname,
                        task=task,
                        date=parse_date(date),
                        start_time=start_time or None,
                        end_time=end_time or None,
                        description=description or '',
                        attachment=attachment
                    )
        else:
            date = request.POST.get('date')
            pname = request.POST.get('pname')
            task = request.POST.get('task')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            description = request.POST.get('description')
            attachment = request.FILES.get('attachment')
            task_obj = Task.objects.get(id=task)
            if pname and task:
                Timesheet.objects.create(
                    emp_id_id=emp_id,
                    pname_id=pname,
                    task=task_obj.title,
                    date=parse_date(date),
                    start_time=start_time or None,
                    end_time=end_time or None,
                    description=description or '',
                    attachment=attachment if attachment else None
                )

        return redirect('update_timesheet', user_id=user_id)


    projects = Project.objects.filter(team_members__id=emp_id)
    tasks = Task.objects.filter(assigned_to_id=emp_id).select_related('project')

    return render(request, 'update_timesheet.html', {
        'projects': projects,
        'days': days,
        'tasks': tasks
    })



def team_task_report(request, user_id):
    user_id = request.session.get('user_id')  # get from session
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    # Get tasks assigned to the user
    tasks = Task.objects.filter(emp_id=user_id).order_by('-id')

    context = {
        'tasks': tasks,
        'total_tasks': tasks.count(),
        'user_id': user_id,
    }

    return render(request, 'team_task_report.html', context)




def task_list_view(request, user_id):
    user_id = request.session.get('user_id')  # get from session
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    # Get tasks assigned to the user
    # tasks = Task.objects.filter(emp_id=user_id)
    employee = emp_registers.objects.get(id=user_id)
    emp_name = employee.name

    # Filter tasks where assigned_to.name matches the employee's name
    tasks = Task.objects.filter(assigned_to__name=emp_name).order_by('-id')

    context = {
        'tasks': tasks,
        'total_tasks': tasks.count(),
        'user_id': user_id,
    }

    return render(request, 'task_list.html', context)






def add_task_view(request, user_id):
    user_id = request.session.get('user_id')
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    emp = emp_registers.objects.filter(id=user_id).first()
    if not emp:
        messages.error(request, "Employee not found.")
        return redirect('login')

    projects = Project.objects.filter(emp_id=emp)
    members = Member.objects.all()

    if request.method == "POST":
        project_id = request.POST.get('project')
        title = request.POST.get('title')
        description = request.POST.get('description')
        assigned_to_id = request.POST.get('assigned_to')
        due_date = request.POST.get('due_date')

        #status = request.POST.get('status')
        priority = request.POST.get('priority')
        p=PriorityMaster.objects.get(level=priority)
        if due_date:
            try:
                due_date_obj = date.fromisoformat(due_date)
                if due_date_obj < date.today():
                    messages.error(request, "Due date cannot be before today.")
                    return render(request, 'add_task.html', {
                        'projects': projects,
                        'members': members,
                        'user_id': user_id
                    })
            except ValueError:
                messages.error(request, "Invalid due date format.")
                return render(request, 'add_task.html', {
                    'projects': projects,
                    'members': members,
                    'user_id': user_id
                })
        try:
            project = Project.objects.get(id=project_id)
            assigned_to = Member.objects.get(id=assigned_to_id)
            status =StatusMaster.objects.get(id=1)
            Task.objects.create(
                emp_id=emp,
                start_date=date.today(),
                project=project,
                title=title,
                description=description,
                assigned_to=assigned_to,
                due_date=due_date if due_date else None,
                status=status,
                priority=p,
                leader=emp.name
            )
            messages.success(request, "Task added successfully.")
            return redirect('task_list', user_id=user_id)
        except Exception as e:
            messages.error(request, f"Error: {e}")

    return render(request, 'add_task.html', {
        'projects': projects,
        'members': members,
        'user_id': user_id
    })




from django.utils.timezone import now

def update_task_status_page(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    user_id = request.session.get('user_id')
    emp = get_object_or_404(emp_registers, id=user_id)
    position = emp.position.role.lower()  # RoleMaster FK

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
    })




def user_timesheet(request):
    user_id = request.session['user_id']  # your user logic
    timesheets = Timesheet.objects.filter(emp_id=user_id).select_related('pname')
    user = timesheets.first().emp_id if timesheets else None
    return render(request, 'user_timesheet.html', {'timesheets': timesheets, 'user': user})
# Step 1: Enter Email




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

            # Send OTP email
            send_mail(
                'Your OTP for Password Reset',
                f'Your OTP is: {otp}',
                'noreply@yourdomain.com',
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





def update_profile(request ,user_id):
    emp = emp_registers.objects.get(id=request.session['user_id'])  # Logged-in user
    profile, created = EmployeeDetail.objects.get_or_create(emp_id=emp)

    if request.method == 'POST':
        # Basic fields
        profile.phone_number = request.POST.get('phone_number')
        profile.guidance_phone_number = request.POST.get('guidance_phone_number')
        profile.address = request.POST.get('address')
        profile.father_guidance_name = request.POST.get('father_guidance_name')
        profile.blood_group = request.POST.get('blood_group')
        profile.permanent_address = request.POST.get('permanent_address')
        profile.total_leave = request.POST.get('total_leave') or 0
        profile.balance_leave = request.POST.get('balance_leave') or 0
        profile.used_leave = request.POST.get('used_leave') or 0
        profile.job_status = request.POST.get('job_status')

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

        # Education & Experience (summary text if any)
        profile.education_info = request.POST.get('education_info')
        profile.experience = request.POST.get('experience')

        # Profile Image Upload
        if 'profile_image' in request.FILES:
            profile.profile_image = request.FILES['profile_image']

        profile.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('update_profile',user_id=user_id)

    # Fetch related models
    educations = Education.objects.filter(emp_id=emp)
    experiences = Experience.objects.filter(emp_id=emp)
    documents = Document.objects.filter(emp_id=emp)

    return render(request, 'update_profile.html', {
        'profile': profile,
        'educations': educations,
        'experiences': experiences,
        'documents': documents,
        'employee_name': emp.name,
    })


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


from django.http import JsonResponse
from django.shortcuts import render
from .models import LeaveTypeMaster, LeaveRecord
import json


def leave_type_panel(request):
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            # Load data from the POST request
            data = json.loads(request.body)
            leave_id = data.get('id')  # Get the leave ID from the POST data
            leave = LeaveTypeMaster.objects.get(id=leave_id)  # Fetch the leave type from DB
            leave_status = data.get('status', True)  # Get the new status (Active or Inactive)
            leave.leave_status = leave_status  # Update the leave status
            leave.save()  # Save the updated leave type

            return JsonResponse({'success': True})  # Return a success response
        except LeaveTypeMaster.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Leave type not found'})  # Handle leave type not found error
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})  # Handle other exceptions

    # For GET request: Show the leave types and leave records
    leave_masters = LeaveTypeMaster.objects.all()
    leave_records = LeaveRecord.objects.all()

    return render(request, 'leave_type_panel.html', {
        'leave_masters': leave_masters,
        'leave_records': leave_records
    })


def project_detail_view(request, pk):
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





