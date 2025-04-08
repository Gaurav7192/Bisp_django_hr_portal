from enum import unique

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from datetime import date,datetime,time,timedelta





class emp_registers(models.Model):
    ROLE_CHOICES = [
        ('HR', 'HR'),
        ('Manager', 'Manager'),
        ('Staff', 'Staff'),
    ]
    JOB_STATUS_CHOICES = [
        ('active', 'Active'),
        ('resign', 'Resign'),
        ('debarred', 'Debarred'),
    ]
    id = models.AutoField(primary_key=True)
    name=models.CharField(max_length=100,null=False)
    email=models.EmailField(unique=True,null=False)
    password=models.CharField(max_length=128,null=False)

    position = models.CharField(max_length=10, choices=ROLE_CHOICES,null=True)
    department = models.CharField(max_length=100, blank=True, null=True)

    registration_date = models.DateTimeField(auto_now_add=True,)
    joindate =models.DateField(null=True)
    reportto=models.CharField(max_length=100,null=False)
    gender_choices = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]

    gender = models.CharField(max_length=10, choices=gender_choices, null=True)
    marriage_status = models.CharField(max_length=20, null=True)
    aadhar_no = models.CharField(max_length=12, unique=True, null=True)
    dob = models.DateField(null=True)
    nationality = models.CharField(max_length=30, null=True)
    religion = models.CharField(max_length=30, null=True)
    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    job_status = models.CharField(max_length=10, choices=JOB_STATUS_CHOICES, default='active')
    def save(self, *args, **kwargs):
        self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name,self.email


# class LeaveRecord(models.Model):
#     EMPLOYEE_TYPES = [('Staff', 'Staff'), ('Manager', 'Manager'), ('HR', 'HR')]
#     DEPARTMENTS = [('IT', 'IT'), ('Accounts', 'Accounts'), ('HR', 'HR'), ('Sales', 'Sales'),('Marketing', 'Marketing')]
#     LEAVE_TYPES = [('Sick Leave', 'Sick Leave'), ('Casual Leave', 'Casual Leave'),
#                        ('Compensation Leave', 'Compensation Leave'), ('Half Day', 'Half Day')]
#     STATUS_TYPES = [('Approved', 'Approved'), ('Rejected', 'Rejected'),
#                         ('Withdrawn', 'Withdrawn'), ('Pending', 'Pending')]
#
#     half_day_type=[('First Half','First Half'),('Second Half','Second Half')]
#     # Foreign Key
#
#     start_date = models.DateField(null=False)
#     end_date=models.DateField(null=False,default=2025-03-27)
#     no_of_days=models.DecimalField(max_digits=4,decimal_places=1)
#     leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
#     half_day=models.CharField(max_length=12,choices=half_day_type,null=True,blank=True)
#     reason = models.TextField()
#     approval_status = models.CharField(max_length=20, choices=STATUS_TYPES)
#     approved_by = models.CharField(max_length=100, blank=True, null=True)
#
#     def __str__(self):
#         return f"{self.name} - {self.leave_type}"
#
#
#
# class employee_leaves(models.Model):
#     pass
# #class EmployeeForm(forms.ModelForm):
#     class Meta:
#         model = emp_registers
#         fields = '__all__'
# #

class emp_logins(models.Model):
    email = models.EmailField()
    login_time = models.DateTimeField(auto_now_add=True)

    remember_me = models.BooleanField(default=False)
    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)


    def __str__(self):
        return self.email



class Member(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)

    def __str__(self):
        return self.name


class Project(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('hold', 'Hold'),
        ('complete', 'Complete'),
        ('claim_complete', 'Claim Complete'),
        ('inprocess', 'In Process'),
    ]

    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]

    RATE_STATUS_CHOICES = [
        ('fixed', 'Fixed'),
        ('hourly', 'Hourly'),
        ('non billable', 'Non Billable'),
        ('billable', 'Billable')
    ]
    emp_id=models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)

    pname = models.CharField(max_length=100,null=True)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=True, blank=True)
    complete_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rate = models.FloatField(default=0.0)
    rate_status = models.CharField(max_length=20, choices=RATE_STATUS_CHOICES, default='fixed')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    description = models.TextField(blank=True, null=True)

    admin = models.CharField(max_length=100)
    manager = models.CharField(max_length=100)
    client = models.CharField(max_length=100)


    team_members = models.ManyToManyField(Member, related_name='projects')

    def __str__(self):
        return self.pname


class Task(models.Model):
    PRIORITY_CHOICES = [
        (1, 'Low'),
        (2, 'Medium'),
        (3, 'High'),
    ]
    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)

    start_date = models.DateField(null=True, blank=True)
    project= models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ForeignKey(Member, on_delete=models.CASCADE)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Project.STATUS_CHOICES, default='pending')
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)
    leader = models.CharField(max_length=100)
    last_update = models.DateTimeField(auto_now=True)
    complete_date=models.DateTimeField(null=True,blank=True)
    def __str__(self):
        return self.title


class EmployeeDetail(models.Model):
    JOB_STATUS_CHOICES = [
        ('active', 'Active'),
        ('resign', 'Resign'),
        ('debarred', 'Debarred'),
    ]

    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)
    phone_number = models.CharField(max_length=15)
    guidance_phone_number = models.CharField(max_length=15)
    address = models.TextField()
    father_guidance_name = models.CharField(max_length=100)
    blood_group = models.CharField(max_length=5)
    permanent_address = models.TextField()
    total_leave=models.FloatField()
    balance_leave = models.FloatField(default=0.0)
    used_leave = models.FloatField(default=0.0)
    job_status = models.CharField(max_length=10, choices=JOB_STATUS_CHOICES, default='active')

    passport = models.CharField(max_length=100, blank=True, null=True)
    passport_no = models.CharField(max_length=50, blank=True, null=True)
    tel = models.CharField(max_length=15, blank=True, null=True)
    nationality = models.CharField(max_length=50, blank=True, null=True)
    religion = models.CharField(max_length=50, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)

    # Emergency Contact - Primary
    primary_contact_name = models.CharField(max_length=100, blank=True, null=True)
    primary_relationship = models.CharField(max_length=50, blank=True, null=True)
    primary_phone = models.CharField(max_length=15, blank=True, null=True)

    # Emergency Contact - Secondary
    secondary_contact_name = models.CharField(max_length=100, blank=True, null=True)
    secondary_relationship = models.CharField(max_length=50, blank=True, null=True)
    secondary_phone = models.CharField(max_length=15, blank=True, null=True)

    # Bank Information
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_no = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)


    def save(self, *args, **kwargs):
        current_date = datetime.now()

        # Fetch joindate from emp_registers table
        if self.emp_id and self.emp_id.joindate:
            joined_year = self.emp_id.joindate.year
            joined_month = self.emp_id.joindate.month

            # If joined in the current year, calculate leave based on the month
            if current_date.year == joined_year:
                self.total_leave = max(12 - joined_month - 1, 0)
            else:
                self.total_leave = 12
        else:
            self.total_leave = 12
            # Ensure used_leave is not negative
        if self.used_leave < 0:
            self.used_leave = 0.0

            # Ensure total_leave is not negative (though it's calculated above)
        if self.total_leave < 0:
            self.total_leave = 0.0
        # Calculate balance leave
        self.balance_leave = max(self.total_leave - self.used_leave, 0)

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.emp_id.name} - {self.emp_id.email} - {self.get_job_status_display()}'





class Experience(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    organization = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.emp_id} - {self.organization}"


class Education(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    year_of_passing = models.IntegerField()
    grade = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.emp_id} - {self.degree}"


class Document(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=100)
    document_name = models.CharField(max_length=255)
    document_file = models.FileField(upload_to='employee_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.emp_id} - {self.document_type}"



class LeaveRecord(models.Model):
    EMPLOYEE_TYPES = [('Staff', 'Staff'), ('Manager', 'Manager'), ('HR', 'HR')]
    DEPARTMENTS = [('IT', 'IT'), ('Accounts', 'Accounts'), ('HR', 'HR'), ('Sales', 'Sales'), ('Marketing', 'Marketing')]
    LEAVE_TYPES = [('Sick Leave', 'Sick Leave'), ('Casual Leave', 'Casual Leave'),
                   ('Compensation Leave', 'Compensation Leave'), ('Half Day', 'Half Day')]
    STATUS_TYPES = [('Approved', 'Approved'), ('Rejected', 'Rejected'),
                     ('Withdrawn', 'Withdrawn'), ('Pending', 'Pending')]
    HALF_DAY_TYPE = [('First Half', 'First Half'), ('Second Half', 'Second Half')]

    emp_id = models.ForeignKey('emp_registers', on_delete=models.DO_NOTHING)

    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False, default=date(2025, 3, 27))
    no_of_days = models.FloatField(default=0.0)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    half_day = models.CharField(max_length=12, choices=HALF_DAY_TYPE, null=True, blank=True)
    reason = models.TextField()
    approval_status = models.CharField(max_length=20, choices=STATUS_TYPES, default='Pending')
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.emp_id.name} - {self.leave_type} - {self.approval_status}"

#
# class EmployeeLeaves(models.Model):
#    # emp_id = models.ForeignKey('emp_registers', on_delete=models.DO_NOTHING)
#     leave_record = models.ForeignKey(LeaveRecord, on_delete=models.DO_NOTHING)
#
    def __str__(self):
        if self.emp_id:
            return f"{self.emp_id.name} - {self.leave_type} - {self.approval_status}"
        else:
            return f"Leave Record (No Employee) - {self.leave_type} - {self.approval_status}"

from django import forms

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = emp_registers
        fields = '__all__'


from django.db import models


class Timesheet(models.Model):
    emp_id = models.ForeignKey('emp_registers', on_delete=models.DO_NOTHING)
    pname = models.ForeignKey('Project', on_delete=models.DO_NOTHING)
    task = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField()
    attachment = models.ImageField(upload_to='attachments/')

    def __str__(self):
        return f"{self.emp_id} - {self.pname} - {self.date}"
