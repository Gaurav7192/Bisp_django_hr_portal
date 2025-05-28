from django.db import models

# Create your models here.
from enum import unique
from datetime import datetime
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from datetime import date,datetime,time,timedelta
from django.db.models import JSONField
import logging
from datetime import timedelta
from django.utils import timezone
logger = logging.getLogger(__name__)
from django.utils.timezone import now
from simple_history.models import HistoricalRecords
from django.conf import settings # Added this import to resolve potential issues if settings is used later

class Designation_master_(models.Model):
    designation_name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.designation_name

class Video_transition_(models.Model): # Added _transition_
    CATEGORY_CHOICES = [
        ('Learning', 'Learning Video'),
        ('Project Management', 'Project Management'),
        ('Task Management', 'Task Management'),
        ('Timesheet', 'Timesheet Management'),
        ('Leave', 'Leave Management'),
        ('User Preference', 'User Preference'),
        ('Exit', 'Exit Management'),
    ]
    title = models.CharField(max_length=200)
    video=models.FileField(upload_to='videos/',null=True)
    url = models.URLField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

class Role_master_(models.Model):
    role = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.role

class Department_master_(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class LeaveType_master_(models.Model):
    MARITAL_STATUS_CHOICES = [
            ('All', 'All'),
            ('Single', 'Single'),
            ('Married', 'Married'),
            ('Divorced', 'Divorced'),
            ('Widow', 'Widow'),
        ]

    GENDER_CHOICES = [
            ('All', 'All'),
            ('Male', 'Male'),
            ('Female', 'Female'),
            ('Other', 'Other'),
        ]

    name = models.CharField(max_length=50, unique=True)

    applicable_gender = models.CharField(
            max_length=10, choices=GENDER_CHOICES, default='All',
            help_text="Which gender can apply for this leave."
        )
    payable=models.BooleanField(default=True)
    applicable_marital_status = models.CharField(
            max_length=10, choices=MARITAL_STATUS_CHOICES, default='All',
            help_text="Which marital status can apply for this leave."
        )

    applicable_department = models.ManyToManyField(
        'Department_master_',
        blank=True,
        help_text="Which departments can apply for this leave. Leave blank or select 'All' for all."
    )

    specific_employees = models.ManyToManyField(
            'emp_registers_transition_', # Updated foreign key reference
            blank=True,
            help_text="If specified, this leave type will apply only to selected employees."
        )

    count_holidays = models.BooleanField(
            default=False,
            help_text="Should holidays be counted in the leave duration?"
        )

    count_weekends = models.BooleanField(
            default=False,
            help_text="Should weekends be counted in the leave duration?"
        )
    leavecode=models.CharField(max_length=10,null=True)
    leave_status=models.BooleanField(default=True)
    description=models.TextField(max_length=100,null=True)
    max_days_allowed=models.IntegerField(null=True)
    carry_forward=models.BooleanField(default=True)
    start_from=models.DateTimeField(null=True)
    end_from=models.DateTimeField(null=True)
    def __str__(self):
        return self.name

class LeaveStatus_master_(models.Model):
    status = models.CharField(max_length=20, unique=True,)

    def __str__(self):
        return self.status

class HalfDayType_master_(models.Model):
    part = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.part

class JobStatus_master_(models.Model):
    status = models.CharField(max_length=20,unique=True)

    def __str__(self):
        return self.status

class emp_registers_transition_(models.Model): # Added _transition_
    id = models.AutoField(primary_key=True)
    name=models.CharField(max_length=100,null=False)
    email=models.EmailField(unique=True,null=False)
    password=models.CharField(max_length=128,null=False)

    position = models.ForeignKey(Role_master_, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(Department_master_, on_delete=models.SET_NULL, null=True)
    designation = models.ForeignKey(Designation_master_, on_delete=models.SET_NULL, null=True, blank=True)

    registration_date = models.DateTimeField(auto_now_add=True,)
    joindate =models.DateField(null=True)
    reportto = models.CharField(max_length=100, null=True, blank=True)

    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    job_status = models.ForeignKey(JobStatus_master_, on_delete=models.SET_NULL, null=True, default=None)
    history = HistoricalRecords()

    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    def is_locked(self):
        return self.account_locked_until and self.account_locked_until > timezone.now()

    def lock_account(self, duration_hours=2):
        self.account_locked_until = timezone.now() + timedelta(hours=duration_hours)
        self.save()

    def unlock_account(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save()

    def save(self, *args, **kwargs):
        self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.email})"

class Handbook_transition_(models.Model): # Added _transition_
    document_name=models.CharField(max_length=100,null =False )
    document = models.FileField(upload_to='handbooks/')
    active_status = models.BooleanField(default=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True)

    employees = models.ManyToManyField(
        'emp_registers_transition_', # Updated foreign key reference
        through='Acknowledgment_transition_', # Updated foreign key reference
        related_name='handbooks'
    )
    history = HistoricalRecords()

    def __str__(self):
        return f"Handbook {self.id} - {self.document.name}"

class Acknowledgment_transition_(models.Model): # Added _transition_
    employee = models.ForeignKey('emp_registers_transition_', on_delete=models.CASCADE) # Updated foreign key reference
    handbook = models.ForeignKey(Handbook_transition_, on_delete=models.CASCADE) # Updated foreign key reference
    acknowledgment_date = models.DateField(null=True )
    AGREEMENT_CHOICES = [
        ('agree', 'Agree'),
        ('disagree', 'Disagree'),
    ]
    acknowledgment = models.CharField(
        max_length=20,
        choices=AGREEMENT_CHOICES,
        default='Not Acknowladge'
    )
    status = models.CharField(max_length=20,
                              default='active')
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.employee.name} - {self.handbook.id} - {self.acknowledgment} - {self.status}"

class emp_logins_transition_(models.Model): # Added _transition_
    email = models.EmailField()
    login_time = models.DateTimeField(auto_now_add=True)
    remember_me = models.BooleanField(default=False)
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    history = HistoricalRecords()

    def __str__(self):
        return self.email

class Member_transition_(models.Model): # Added _transition_
    name = models.CharField(max_length=100)
    email = models.EmailField()
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    history = HistoricalRecords()

    def __str__(self):
        return self.name

class RateStatus_master_(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status

class Status_master_(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status

class Priority_master_(models.Model):
    level = models.PositiveSmallIntegerField(unique=True)
    label = models.CharField(max_length=10)

    def __str__(self):
        return self.label

class Project_transition_(models.Model): # Added _transition_
    emp_id=models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference

    pname = models.CharField(max_length=100,null=True)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=True, blank=True)
    complete_date = models.DateField(null=True, blank=True)

    rate = models.FloatField(default=0.0)
    status = models.ForeignKey(Status_master_, on_delete=models.SET_NULL, null=True, default=None)
    rate_status = models.ForeignKey(RateStatus_master_, on_delete=models.SET_NULL, null=True, default=None)
    priority = models.ForeignKey(Priority_master_, on_delete=models.SET_NULL, null=True, default=None)

    description = models.TextField(blank=True, null=True)

    admin = models.CharField(max_length=100)
    manager = models.CharField(max_length=100)
    client = models.CharField(max_length=100)

    last_update =models.DateTimeField(auto_now=True,null=True)
    team_members = models.ManyToManyField(Member_transition_, related_name='projects') # Updated foreign key reference
    history = HistoricalRecords()

    def __str__(self):
        return self.pname

class Task_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference

    start_date = models.DateField(null=True, blank=True)
    project= models.ForeignKey(Project_transition_, on_delete=models.CASCADE, related_name='tasks') # Updated foreign key reference
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ManyToManyField(Member_transition_) # Updated foreign key reference

    due_date = models.DateField(null=True, blank=True)
    status = models.ForeignKey(Status_master_, on_delete=models.SET_NULL, null=True, default=None)

    priority = models.ForeignKey(Priority_master_, on_delete=models.SET_NULL, null=True, default=None)

    leader = models.CharField(max_length=100)
    last_update = models.DateTimeField(auto_now=True)
    complete_date=models.DateTimeField(null=True,blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return self.title

class EmployeeDetail_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    phone_number = models.CharField(max_length=15)
    guidance_phone_number = models.CharField(max_length=15)
    address = models.TextField()
    father_guidance_name = models.CharField(max_length=100)
    blood_group = models.CharField(max_length=5)
    permanent_address = models.TextField()
    total_leave=models.FloatField()
    balance_leave = models.FloatField(default=0.0)
    used_leave = models.FloatField(default=0.0)
    job_status = models.ForeignKey(JobStatus_master_, on_delete=models.SET_NULL, null=True, default=None)
    gender_choices = [('male', 'Male'), ('female', 'Female'), ('other', 'Other')]

    gender = models.CharField(max_length=10, choices=gender_choices, null=True)

    aadhar_no = models.CharField(max_length=12, unique=True, null=True)
    dob = models.DateField(null=True)

    profile_pic = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
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

    secondary_contact_name = models.CharField(max_length=100, blank=True, null=True)
    secondary_relationship = models.CharField(max_length=50, blank=True, null=True)
    secondary_phone = models.CharField(max_length=15, blank=True, null=True)

    # Bank Information
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    bank_account_no = models.CharField(max_length=50, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    pan_no = models.CharField(max_length=20, blank=True, null=True)

    leave_details = JSONField(default=dict, blank=True)
    history = HistoricalRecords()

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

        super().save(*args, **kwargs)

    def update_leave_balance(self, leave_type, no_of_days, action="add"):
        """
        Updates the leave balance for a specific leave type for this employee.
        """
        # Initialize the leave type if it does not exist
        if leave_type not in self.leave_details:
            self.leave_details[leave_type] = {
                "total_leave": 12,  # Default total leave (can be set based on the type)
                "used_leave": 0,
                "balance_leave": 12  # Default balance leave
            }

        # Get current leave data
        leave_data = self.leave_details[leave_type]

        # Action to be performed: "add" or "subtract"
        if action == "add":
            leave_data["used_leave"] += no_of_days
            leave_data["balance_leave"] -= no_of_days
        elif action == "subtract":
            leave_data["used_leave"] -= no_of_days
            leave_data["balance_leave"] += no_of_days

        # Save updated leave data
        self.leave_details[leave_type] = leave_data
        self.save()

    def __str__(self):
        return f'{self.emp_id.name} - {self.emp_id.email} '

class EmployeeDetailHistory_transition_(models.Model): # Added _transition_
    employee = models.ForeignKey(EmployeeDetail_transition_, on_delete=models.DO_NOTHING) # Updated foreign key reference
    start_date = models.DateTimeField(null=True, blank=True)
    change_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING, null=True, blank=True) # Updated foreign key reference
    changed_fields = models.TextField()
    previous_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"History for {self.employee.emp_id.name} on {self.change_date}"

class Experience_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.CASCADE) # Updated foreign key reference
    organization = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)
    added_date=models.DateField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.emp_id} - {self.organization}"

class Education_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.CASCADE) # Updated foreign key reference
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    year_of_passing = models.IntegerField()
    grade = models.CharField(max_length=50, blank=True)
    added_date = models.DateField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.emp_id} - {self.degree}"

class Document_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.CASCADE) # Updated foreign key reference
    document_type = models.CharField(max_length=100)
    document_name = models.CharField(max_length=255)
    document_file = models.FileField(upload_to='employee_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.emp_id} - {self.document_type}"

class LeaveHalfDay_transition_(models.Model): # Added _transition_
    """
    This model links a half-day entry to a specific leave record and allows tracking of the date and type of half-day.
    """
    half_day_type = models.ForeignKey(HalfDayType_master_, on_delete=models.CASCADE)
    half_day_date = models.DateField()
    history = HistoricalRecords()

    def __str__(self):
        return f"Half Day Type: {self.half_day_type.part} on {self.half_day_date}"

class LeaveRecord_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False, default=date(2025, 3, 27))
    no_of_days = models.FloatField(default=0.0)
    history = HistoricalRecords()

    leave_type = models.ForeignKey(LeaveType_master_, on_delete=models.SET_NULL, null=True)

    approval_status = models.ForeignKey(LeaveStatus_master_, on_delete=models.SET_NULL, null=True, default=None)
    approve_reason=models.TextField(null=True)
    reason = models.TextField()
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    compensatory_leave=models.BooleanField(default=False)
    compensatory_leave_reason=models.TextField(null =True )
    document = models.FileField(upload_to='leave_documents/',null=True)
    half_day = models.ManyToManyField(LeaveHalfDay_transition_, blank=True) # Updated foreign key reference

    def __str__(self):
        if self.emp_id:
            return f"{self.emp_id.name} - {self.leave_type} - {self.approval_status}"
        else:
            return f"Leave Record (No Employee) - {self.leave_type} - {self.approval_status}"

class EmployeeForm(models.Model): # This class seems out of place as a Model, typically it's a forms.Form or forms.ModelForm
    class Meta:
        model = emp_registers_transition_ # Updated foreign key reference
        fields = '__all__'

class Timesheet_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    pname = models.ForeignKey('Project_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    task = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    description = models.TextField(null=True)
    attachment = models.ImageField(upload_to='attachments/')
    upload_on=models.DateField(null=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.emp_id} - {self.pname} - {self.date}"

class Holiday_transition_(models.Model): # Added _transition_
    name = models.CharField(max_length=100)
    date = models.DateField()
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.date})"

class Attendance_transition_(models.Model): # Added _transition_
    emp_id = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    date = models.DateField()
    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)
    history = HistoricalRecords()

    class Meta:
        unique_together = ('date', 'emp_id')

    def __str__(self):
        return f"{self.emp_id.name} - {self.date}"

class ResignationStatus_master_(models.Model):
    status_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.status_name

class Resignation_transition_(models.Model): # Added _transition_
    """Base resignation form info."""
    employee = models.ForeignKey('emp_registers_transition_', on_delete=models.CASCADE) # Updated foreign key reference
    resign_date = models.DateField()
    last_date = models.DateField()
    reason = models.TextField()
    selected_elsewhere = models.BooleanField(default=False)
    bond_over = models.BooleanField(default=False)
    advance_salary = models.BooleanField(default=False)
    dues_pending = models.BooleanField(default=False)
    resign_status =models.ForeignKey(ResignationStatus_master_,on_delete=models.DO_NOTHING)
    history = HistoricalRecords()

    def __str__(self):
        return f"Resignation of {self.employee.name}"

class ResignStatusAction_transition_(models.Model): # Added _transition_
    """Tracks status changes for a resignation."""
    resignation = models.ForeignKey(Resignation_transition_, on_delete=models.CASCADE, related_name='status_actions') # Updated foreign key reference
    action = models.CharField(max_length=255)
    action_by = models.ForeignKey('emp_registers_transition_', on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='resign_actions') # Updated foreign key reference
    action_date = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.resignation.employee.name} - {self.action} on {self.action_date.strftime('%Y-%m-%d')}"

class ActionChecklist_transition_(models.Model): # Added _transition_
    """Each checkbox field as a separate boolean column."""
    resignation = models.OneToOneField(Resignation_transition_, on_delete=models.CASCADE, related_name='checklist') # Updated foreign key reference

    # Knowledge Transfer
    status_ongoing_projects = models.BooleanField(default=False)
    outstanding_tasks = models.BooleanField(default=False)
    important_contacts = models.BooleanField(default=False)

    # IT Permissions and Access
    update_passwords = models.BooleanField(default=False)
    revoke_access = models.BooleanField(default=False)
    remove_from_payroll = models.BooleanField(default=False)
    update_employee_directory = models.BooleanField(default=False)

    # Paperwork
    official_resignation_letter = models.BooleanField(default=False)
    last_paycheck_arrangements = models.BooleanField(default=False)
    nda = models.BooleanField(default=False)

    # Recover Assets
    laptop_and_charger = models.BooleanField(default=False)
    mouse = models.BooleanField(default=False)

    # Exit Interview
    exit_interview_conducted = models.BooleanField(default=False)

    # Announce Departure
    send_announcement = models.BooleanField(default=False)
    give_farewell_party = models.BooleanField(default=False)
    history = HistoricalRecords()

    def __str__(self):
        return f"Checklist for {self.resignation.employee.name}"

class SentEmail_transition_(models.Model): # Added _transition_
    employee = models.ForeignKey('emp_registers_transition_', on_delete=models.DO_NOTHING) # Updated foreign key reference
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Email to {self.recipient_email} by {self.employee} on {self.sent_at.strftime('%Y-%m-%d')}"
