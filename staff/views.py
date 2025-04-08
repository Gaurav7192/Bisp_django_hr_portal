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
            dob = cleaned_data.get('dob')
            joindate = cleaned_data.get('joindate')
            gender = cleaned_data.get('gender')
            aadhar_no = cleaned_data.get('aadhar_no')
            nationality = cleaned_data.get('nationality')
            religion = cleaned_data.get('religion')
            reportto = cleaned_data.get('reportto')
            marriage_status = cleaned_data.get('marriage_status')

            #1. Check if all fields are filled
            if not all([name, email, position, department, dob, joindate, gender, aadhar_no, nationality, religion,
                        reportto]):
                messages.error(request, 'All fields are required!')
                return redirect('update_employee', id=id)

            # 2. Validate Name
            if not re.match(r'^[A-Za-z\s]+$', name):
                messages.error(request, 'Invalid name. Only letters and spaces are allowed.')
                return redirect('update_employee', id=id)

            #3. Validate Email
            if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                messages.error(request, 'Invalid email address.')
                return redirect('update_employee', id=id)

            # 4. Validate Password (Only if it is updated)
            if password:
                if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]',
                                                                                           password) or not re.search(
                        r'[!@#$%^&*]', password):
                    messages.error(request,
                                   'Password must be at least 8 characters, including one uppercase letter, one number, and one special character.')
                    return redirect('update_employee', id=id)

            # 5. Validate Dates
            try:
                if dob >= datetime.today().date():
                    messages.error(request, 'Invalid Date of Birth. It cannot be today or in the future.')
                    return redirect('update_employee', id=id)

                if dob > datetime.today().date() - timedelta(days=18 * 365):
                    messages.error(request, 'Staff must be at least 18 years old.')
                    return redirect('update_employee', id=id)

                if joindate > datetime.today().date():
                    messages.error(request, 'Joining date cannot be in the future.')
                    return redirect('update_employee', id=id)

                if joindate < datetime(2025, 1, 1).date():
                    messages.error(request, 'Joining date cannot be before January 1, 2025.')
                    return redirect('update_employee', id=id)
            except ValueError:
                messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
                return redirect('update_employee', id=id)

            # 6. Validate Aadhar Number
            if not re.match(r'^\d{12}$', str(aadhar_no)):
                messages.error(request, 'Invalid Aadhar number. It must be 12 digits.')
                return redirect('update_employee', id=id)

            # 7. Save Data
            form.save()
            messages.success(request, "Employee details updated successfully!")
            return redirect('employee_list')
        else:
            messages.error(request, "Failed to update. Please check the form for errors.")
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
              #  request.session['postion']=user.position
               # request.session['img']=user.profile_pic.url

                if remember_me:
                    request.session.set_expiry(604800)  # 1 week
                else:
                    request.session.set_expiry(0)

                if user.position == 'HR':
                    return redirect('d1', id=user.id)
                else:
                    return redirect('d2', id=user.id)
            else:
                messages.error(request, 'Invalid email or password.')
        except emp_registers.DoesNotExist:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'login.html')



#
# def staff_registration(request):
#     return render(request ,'staff registration.html')

def staff_registration(request, id):
    user = emp_registers.objects.filter(id=id)  # Get the current user

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)  # Bind form with submitted data

        if form.is_valid():
            form.save()  # Save if valid
            messages.success(request, 'Staff registration successful!')
            return redirect('staff_registration', id=id)  # Redirect after success
        else:
            messages.error(request, 'Please correct the errors below.')  # Keep form data

    else:
        form = EmployeeForm()  # Empty form for GET request

    return render(request, 'staff registration.html', {'form': form, 'user': user, 'id': id})  # Send form to template

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
    projects = Project.objects.prefetch_related('team_members__emp_id').all()
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
# def staff_registration(request,id):
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
#             return redirect('staff_registration',id=id)
#
#         if not re.match(r'^[a-zA-Z ]+$', name):
#             messages.error(request, 'Invalid name. Only letters and spaces are allowed.')
#             return redirect('staff_registration',id=id)
#         if name.startswith(' '):
#             messages.error(request, 'Name should not start with a space.')
#             return redirect('staff_registration',id=id)
#
#         if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
#             messages.error(request, 'Invalid email address.')
#             return redirect('staff_registration',id=id)
#
#         if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password) or not re.search(r'[!@#$%^&*]', password):
#             messages.error(request, 'Password must be at least 8 characters, including one uppercase letter, one number, and one special character.')
#             return redirect('staff_registration',id=id)
#
#         if password != rpassword:
#             messages.error(request, 'Passwords do not match.')
#             return redirect('staff_registration',id=id)
#
#         try:
#             dob_date = datetime.strptime(dob, '%Y-%m-%d').date()
#             joindate_date = datetime.strptime(joindate, '%Y-%m-%d').date()
#
#             if dob_date >= datetime.today().date():
#                 messages.error(request, 'Invalid Date of Birth.')
#                 return redirect('staff_registration',id=id)
#             if dob_date < date(1980, 1, 1):
#                 messages.error(request, 'date of birth not more than 1980.')
#                 return redirect('staff_registration',id=id)
#
#
#             if dob_date > datetime.today().date() - timedelta(days=18*365):
#                 messages.error(request, 'Staff must be at least 18 years old.')
#                 return redirect('staff_registration',id=id)
#
#             # if joindate_date > datetime.today().date():
#             #     messages.error(request, 'Joining date cannot be in the future.')
#             #     return redirect('staff_registration',id=id)
#
#             if joindate_date < datetime(2025, 1, 1).date():
#                 messages.error(request, 'Joining date cannot be before January 1, 2025.')
#                 return redirect('staff_registration',id=id)
#             if user.position.lower() == 'manager':
#                 if position == 'Manager' or position == 'HR':
#                     messages.error(request, 'Manager only add staff position ')
#                     return redirect('staff_registration', id=id)
#             if user.position.lower()== 'staff':
#                 messages.error(request,message="staff are not allow member")
#                 return ()
#
#
#             # if joindate_date > datetime.today().date():
#             #     messages.error(request, 'Joining date cannot be after the current date.')
#             #     return redirect('staff_registration',id=id)
#         except ValueError:
#             messages.error(request, 'Invalid date format. Please use YYYY-MM-DD.')
#             return redirect('staff_registration',id=id)
#
#         if not re.match(r'^\d{12}$', aadhar_no):
#             messages.error(request, 'Invalid Aadhar number. It must be 12 digits.')
#             return redirect('staff_registration',id=id)
#
#         if emp_registers.objects.filter(email=email).exists():
#             messages.error(request, 'Email already exists!')
#             return redirect('staff_registration',id=id)
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
#         messages.success(request, 'Staff registration successful!')
#        # time.sleep(3)
#         return redirect('staff_registration',id=id)
#
#     return render(request,'staff registration.html',{'user': user, 'id': id})



def add_project_view(request, user_id):
    user_id = request.session.get('user_id')
    try:
        emp = emp_registers.objects.get(id=user_id)  # Fetch employee object
        admin_name = emp.name  # Retrieve employee's name for admin field
    except emp_registers.DoesNotExist:
        messages.error(request, "Employee not found.")
        return redirect('login')
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    managers =emp_registers.objects.filter(position__iexact='manager')
    staff_members =emp_registers.objects.filter(position__iexact='staff')

    if request.method == "POST":
        pname = request.POST.get('pname')
        start_date = request.POST.get('start_date') or None
        end_date = request.POST.get('end_date') or None
        complete_date = request.POST.get('complete_date')or None
        status = request.POST.get('status')
        rate = request.POST.get('rate')
        rate_status = request.POST.get('rate_status')
        priority = request.POST.get('priority')
        description = request.POST.get('description')
        client = request.POST.get('client')
        manager_emp_id = request.POST.get('manager')  # Fetch selected manager emp_id
        team_member_ids = request.POST.getlist('team_members')

        # Fetch the manager object based on emp_id
        manager = emp_registers.objects.filter(position__iexact='manager').first()

        # Create new project
        project = Project.objects.create(
            emp_id=emp,
            pname=pname,
            start_date=start_date,
            end_date=end_date,
            complete_date=complete_date,
            status=status,
            rate=rate,
            rate_status=rate_status,
            priority=priority,
            description=description,
            admin= admin_name, # Assuming admin is the logged-in user
            manager=manager.name if manager else None,  # Store manager's name
            client=client
        )

        # Add team members
        # team_members = Member.objects.filter(id__in=team_member_ids)
        # project.team_members.set(team_members)
        #
        # messages.success(request, "Project created successfully!")
        # return redirect('project',user_id=user_id)
        team_members = []
        for emp_id in team_member_ids:
            employee = emp_registers.objects.filter(id=emp_id).first()  # Find the employee
            if employee:
                # Check if the member already exists
                member, created = Member.objects.get_or_create(emp_id=employee, defaults={'name': employee.name,
                                                                                          'email': f"{employee.name.lower()}@example.com"})
                team_members.append(member)

        # ✅ Assign team members to the project
        project.team_members.set(team_members)

        messages.success(request, "Project created successfully!")
        return redirect('project',user_id=user_id)

    return render(request, 'add_project.html', {
        'user_id': user_id,
        'managers': managers,
        'staff_members': staff_members
    })


def add_employee(request):
    return redirect('staff registration')

def employee_list(request):
    position_filter = request.GET.get('position', '')
    department_filter = request.GET.get('department', '')

    employees = emp_registers.objects.all()

    if position_filter:
            employees = employees.filter(position=position_filter)
    if department_filter:
        employees = employees.filter(department=department_filter)

    department_choices = emp_registers.objects.values_list('department', flat=True).distinct()

    return render(request, 'employee_list.html', {
            'employees': employees,
            'department_choices': department_choices
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
    leave_records = LeaveRecord.objects.filter(query).order_by('-start_date')

    return render(request, 'leave_record.html', {'leave_record': leave_records})



import random




def delete_employee(request, id):
    employee = get_object_or_404(emp_registers, id=id)
    employee.delete()
    messages.success(request, "emp_registers deleted successfully!")
    return redirect('employee_list')




def apply_leave(request, user_id):
    if not user_id:
        user_id = request.session.get('user_id')

    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    try:
        employee = EmployeeDetail.objects.get(emp_id=user_id)
    except EmployeeDetail.DoesNotExist:
        messages.error(request, "Employee details not found.")
        return redirect('login')

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        leave_type = request.POST.get('leave_type')
        reason = request.POST.get('reason')

        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        half_day_data = request.POST.getlist('half_day[]')  # Get half-day selections
        half_day_dict = {}
        for entry in half_day_data:
            if entry:
                date, half = entry.rsplit('-', 1)
                half_day_dict[date] = half

        # Calculate leave days
        leave_days = 0.0
        current_date = start_date

        while current_date <= end_date:
            str_date = str(current_date)
            if str_date in half_day_dict:
                leave_days += 0.5  # Half-day leave
            else:
                leave_days += 1.0  # Full-day leave
            current_date += timedelta(days=1)

        # Check if leave balance is sufficient
        if employee.balance_leave >= leave_days:
            emp_instance = EmployeeDetail.objects.get(emp_id=user_id).emp_id
            leave_application = LeaveRecord(
                emp_id=emp_instance,
                start_date=start_date,
                end_date=end_date,
                no_of_days=leave_days,
                leave_type=leave_type,
                reason=reason,
                approval_status='Pending'
            )
            leave_application.save()

            employee.balance_leave -= leave_days
            employee.used_leave += leave_days
            employee.save()

            messages.success(request, "Leave application submitted successfully!")
            return redirect('apply_leave', user_id=user_id)
        else:
            messages.error(request, "Insufficient leave balance.")

    return render(request, 'apply_leave.html', {
        'employee': employee,
        'balance_leave': employee.balance_leave,
        'used_leave': employee.used_leave
    })





def update_total_leaves():
    current_year = date.today().year
    employees = emp_registers.objects.all()  # Fetch all employees from emp_registers

    if not employees:
        return JsonResponse({"status": "error", "message": "No employee records found."})

    for emp in employees:
        # Calculate total leaves based on position and join date
        if emp.position == 'HR':
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
    leave_records = LeaveRecord.objects.filter(emp_id=user_id).order_by('-start_date').values(
        'id', 'created_at', 'start_date', 'end_date', 'no_of_days', 'reason', 'approval_status', 'emp_id'
    )

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
                'leave_id': leave['id']
            })
        except emp_registers.DoesNotExist:
            continue  # Skip if employee data not found

    # Render the dashboard template with the leave data
    return render(request, 'leave_dashboard.html', {
        'leave_data': leave_data,
        'username': username,
        'today': today
    })


#this is working do not touch
def update_leave_status(request,user_id):
    if request.method == "POST":
        leave_id = request.POST.get("leave_id")
        action = request.POST.get("action")

        # Get the leave record
        leave_record = get_object_or_404(LeaveRecord, id=leave_id)

        # Process the approval or rejection
        if leave_record.approval_status == "Pending":  # Only process if it's pending
            if action.lower() == "approve":
                leave_record.approval_status = "Approved"
                approver = emp_registers.objects.get(id=user_id)

                # Assign the employee's name to approved_by
                leave_record.approved_by = approver.name
                # Set the approver's name
            elif action.lower() == "reject":
                leave_record.approval_status = "Rejected"
                approver = emp_registers.objects.get(id=user_id)

                # Assign the employee's name to approved_by
                leave_record.approved_by = approver.name
                # Increase the employee's total leave balance if rejected
            employee = EmployeeDetail.objects.get(emp_id=leave_record.emp_id)  # Fetch the instance
            employee.balance_leave += leave_record.no_of_days
            employee.used_leave-=leave_record.no_of_days
                # Save the updated leave balance

            # Save the leave record
            leave_record.save()
            employee.save()
            # Return the updated status and approved_by information
            return JsonResponse({
                "status": leave_record.approval_status,
                "approved_by": leave_record.approved_by if action == "approve" else None
            })
        if leave_record.approval_status.lower() != "rejected":
            if now().date() <= leave_record.start_date:
                if action.lower() == "withdraw":

                    leave_record.approval_status = "Withdrawn"
                    leave_record.save()
                    approver = emp_registers.objects.get(id=user_id)
                    emp = EmployeeDetail.objects.get(emp_id=approver.id)  # Get the approver's employee details

                    # Adjust the employee's leave balance
                    emp.balance_leave += leave_record.no_of_leaves  # Add the number of leave days back to balance
                    emp.used_leave -= leave_record.no_of_leaves  # Subtract from used leave
                    emp.save()
        else:
            return JsonResponse({"error": "Cannot withdraw, start date has passed."}, status=400)
    return JsonResponse({"error": "Invalid request"}, status=400)



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

    if request.method == 'POST':
        emp_id = request.session.get('user_id')
        is_weekly = 'weekly' in request.POST  # Correct checkbox handling
        print("POST keys:", request.POST.keys())
        print("Checkbox value for 'weekly':", request.POST.get('weekly'))

        if is_weekly:

            for day in days:
                date = request.POST.get(f'date_{day}')
                pname = request.POST.get(f'pname_{day}')
                task = request.POST.get(f'task_{day}')
                start_time = request.POST.get(f'start_time_{day}')
                end_time = request.POST.get(f'end_time_{day}')
                description = request.POST.get(f'description_{day}')
                attachment = request.FILES.get(f'attachment_{day}')

                print(f"Processing {day}: date={date}, pname={pname}, task={task}")

                # Save only if key fields are provided
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
                    return redirect(update_timesheet)
                    # Weekly timesheet mode
        else:  # Daily timesheet mode
            date = request.POST.get('date')
            pname = request.POST.get('pname')
            task = request.POST.get('task')
            start_time = request.POST.get('start_time')
            end_time = request.POST.get('end_time')
            description = request.POST.get('description')
            attachment = request.FILES.get('attachment')
            print(f"Processing {day} -> Date: {date}, Project: {pname}, Task: {task}")

            if  pname and task:
                Timesheet.objects.create(
                    emp_id_id=emp_id,
                    pname_id=pname,
                    task=task,
                    date=parse_date(date),
                    start_time=start_time if start_time else None,
                    end_time=end_time if end_time else None,
                    description=description or '',
                    attachment=attachment if attachment else None
                )

        return redirect('update_timesheet', user_id=user_id)

    # GET request
    projects = Project.objects.all()
    return render(request, 'update_timesheet.html', {'projects': projects, 'days': days})




def team_task_report(request, user_id):
    user_id = request.session.get('user_id')  # get from session
    if not user_id:
        messages.error(request, "User not logged in.")
        return redirect('login')

    # Get tasks assigned to the user
    tasks = Task.objects.filter(emp_id=user_id)

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
    tasks = Task.objects.filter(assigned_to__name=emp_name)

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

        status = request.POST.get('status')
        priority = request.POST.get('priority')

        try:
            project = Project.objects.get(id=project_id)
            assigned_to = Member.objects.get(id=assigned_to_id)
            Task.objects.create(
                emp_id=emp,
                start_date=date.today(),
                project=project,
                title=title,
                description=description,
                assigned_to=assigned_to,
                due_date=due_date if due_date else None,
                #status=status,
                priority=priority,
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






def update_task_status_page(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    user_id = request.session.get('user_id')
    emp = get_object_or_404(emp_registers, id=user_id)
    position = emp.position.lower()

    # Available statuses based on position
    status_display = {
        'pending': 'Pending',
        'hold': 'Hold',
        'complete': 'Complete',
        'claim_complete': 'Claim Complete',
        'inprocess': 'In Process'
    }

    if position == "staff":
        if task.status.lower()=='complete':
            allowed_keys=['complete']
        else:
            allowed_keys = ['hold', 'inprocess', 'claim_complete', 'complete', 'pending']
    elif position in ['manager', 'hr']:
        if task.status.lower()=='complete':
            allowed_keys=['complete']
        else:
            allowed_keys = ['hold', 'inprocess', 'complete', 'pending']
    else:
        allowed_keys = []
    status_options = [(key, status_display[key]) for key in allowed_keys]

    if task.status.lower() != 'complete':
        if request.method == "POST":
            new_status = request.POST.get("status")
           # print("Form submitted with status:", new_status)  # Debug

            if new_status in allowed_keys:
                task.status = new_status
                if new_status=='complete':
                    pass
                    task.complete_date=now()
                task.save()
            #print("Task status updated to:", task.status)
            # else:
            #     print("Invalid status value submitted:", new_status)

            return redirect("task_list_view", user_id=user_id)


    return render(request, "update_task_status.html", {
        "task": task,
        "status_options": status_options,
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



from django.shortcuts import render, redirect
from django.contrib import messages
from .models import emp_registers, EmployeeDetail, Education, Experience, Document

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
