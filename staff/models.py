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
class DesignationMaster(models.Model):
    designation_name = models.CharField(max_length=100, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.designation_name
class Video(models.Model):
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

    def __str__(self):
        return f"{self.title} ({self.get_category_display()})"

class RoleMaster(models.Model):
    role = models.CharField(max_length=50, unique=True)  # No need for choices anymore

    def __str__(self):
        return self.role
class DepartmentMaster(models.Model):
    name = models.CharField(max_length=50, unique=True)  # Remove 'choices' to allow custom entries

    def __str__(self):
        return self.name


    def __str__(self):
        return self.name

    from django.conf import settings

class LeaveTypeMaster(models.Model):
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
        'DepartmentMaster',
        blank=True,
        help_text="Which departments can apply for this leave. Leave blank or select 'All' for all."
    )

    specific_employees = models.ManyToManyField(
            'emp_registers', blank=True,
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

    def __str__(self):
        return self.name




class LeaveStatusMaster(models.Model):
    status = models.CharField(max_length=20, unique=True,)

    def __str__(self):
        return self.status


class HalfDayTypeMaster(models.Model):
    part = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.part





class JobStatusMaster(models.Model):
    status = models.CharField(max_length=20,unique=True)

    def __str__(self):
        return self.status

class emp_registers(models.Model):

    id = models.AutoField(primary_key=True)
    name=models.CharField(max_length=100,null=False)
    email=models.EmailField(unique=True,null=False)
    password=models.CharField(max_length=128,null=False)

    position = models.ForeignKey(RoleMaster, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(DepartmentMaster, on_delete=models.SET_NULL, null=True)
    designation = models.ForeignKey(DesignationMaster, on_delete=models.SET_NULL, null=True, blank=True)

    registration_date = models.DateTimeField(auto_now_add=True,)
    joindate =models.DateField(null=True)
    reportto = models.CharField(max_length=100, null=True, blank=True)


    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,  # Can be NULL in the database
        blank=True  # Can be left blank in forms
    )
    job_status = models.ForeignKey(JobStatusMaster, on_delete=models.SET_NULL, null=True, default=None)
    history = HistoricalRecords()

    failed_login_attempts = models.IntegerField(default=0)
    account_locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

    def is_locked(self):
        return self.account_locked_until and self.account_locked_until > timezone.now()

    def lock_account(self, duration_hours=2):
        self.account_locked_until = timezone.now() + timedelta(hours=duration_hours)
        self.save()

    def unlock_account(self):
        self.failed_login_attempts = 0
        self.account_locked_until = None
        self.save()



    def __str__(self):
        return f"{self.name} ({self.email})"



class Handbook(models.Model):
    document_name=models.CharField(max_length=100,null =False )
    document = models.FileField(upload_to='handbooks/')  # Path to store the document
    active_status = models.BooleanField(default=True)  # Active status of the handbook
    start_date = models.DateField()  # Start date of validity
    end_date = models.DateField(null=True)  # End date of validity

    # Acknowledgment many-to-many relationship using Employee (emp_registers)
    employees = models.ManyToManyField(
        emp_registers,
        through='Acknowledgment',  # Through the Acknowledgment model
        related_name='handbooks'
    )

    def __str__(self):
        return f"Handbook {self.id} - {self.document.name}"


# Acknowledgment model to track employee responses (preserving history)

class Acknowledgment(models.Model):
    employee = models.ForeignKey(emp_registers, on_delete=models.CASCADE)  # Employee who acknowledged
    handbook = models.ForeignKey(Handbook, on_delete=models.CASCADE)  # Handbook being acknowledged
    acknowledgment_date = models.DateField(null=True )  # Date of acknowledgment
    AGREEMENT_CHOICES = [
        ('agree', 'Agree'),
        ('disagree', 'Disagree'),
    ]
    '''class MyModel(models.Model):
    agreement = models.CharField(
        max_length=15,
        choices=AGREEMENT_CHOICES,
        default='not_acknowledged',  # Default to 'Not Acknowledged'
        blank=False,   # Make it required
    )
    
    def clean(self):
        # Enforce that the value must be 'agree' or 'disagree'
        if self.agreement == 'not_acknowledged':
            raise ValidationError("You must select Agree or Disagree.")'''
    acknowledgment = models.CharField(
        max_length=20,
        choices=AGREEMENT_CHOICES,
        default='Not Acknowladge'  # Default to 'agree'
    )
    status = models.CharField(max_length=20,
                              default='active')  # Status to track the acknowledgment (e.g., 'active', 'revoked')

    def __str__(self):
        return f"{self.employee.name} - {self.handbook.id} - {self.acknowledgment} - {self.status}"
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
    email = models.EmailField()
    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)



    def __str__(self):
        return self.name




class RateStatusMaster(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status



class StatusMaster(models.Model):
    status = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.status



class PriorityMaster(models.Model):
    level = models.PositiveSmallIntegerField(unique=True)
    label = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.get_level_display()}"

class Project(models.Model):
    emp_id=models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)

    pname = models.CharField(max_length=100,null=True)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=True, blank=True)
    complete_date = models.DateField(null=True, blank=True)

    rate = models.FloatField(default=0.0)
    status = models.ForeignKey(StatusMaster, on_delete=models.SET_NULL, null=True, default=None)
    rate_status = models.ForeignKey(RateStatusMaster, on_delete=models.SET_NULL, null=True, default=None)
    priority = models.ForeignKey(PriorityMaster, on_delete=models.SET_NULL, null=True, default=None)

    description = models.TextField(blank=True, null=True)

    admin = models.CharField(max_length=100)
    manager = models.CharField(max_length=100)
    client = models.CharField(max_length=100)

    last_update =models.DateTimeField(auto_now=True,null=True)
    team_members = models.ManyToManyField(Member, related_name='projects')
    history = HistoricalRecords()

    def __str__(self):
        return self.pname


class Task(models.Model):

    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)

    start_date = models.DateField(null=True, blank=True)
    project= models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField()
    assigned_to = models.ManyToManyField(Member)

    due_date = models.DateField(null=True, blank=True)
    status = models.ForeignKey(StatusMaster, on_delete=models.SET_NULL, null=True, default=None)

    priority = models.ForeignKey(PriorityMaster, on_delete=models.SET_NULL, null=True, default=None)

    leader = models.CharField(max_length=100)
    last_update = models.DateTimeField(auto_now=True)
    complete_date=models.DateTimeField(null=True,blank=True)
    def __str__(self):
        return self.title


class EmployeeDetail(models.Model):

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
    job_status = models.ForeignKey(JobStatusMaster, on_delete=models.SET_NULL, null=True, default=None)
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

    # leave_details can store a dictionary like:
    # {
    #     "Annual Leave": {"total_leave": 12, "used_leave": 0, "balance_leave": 12},
    #     "Sick Leave": {"total_leave": 10, "used_leave": 2, "balance_leave": 8},
    # }

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



class EmployeeDetailHistory(models.Model):
    employee = models.ForeignKey(EmployeeDetail, on_delete=models.DO_NOTHING)
    start_date = models.DateTimeField(null=True, blank=True)
    change_date = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING, null=True, blank=True)
    changed_fields = models.TextField()
    previous_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"History for {self.employee.emp_id.name} on {self.change_date}"

class Experience(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    organization = models.CharField(max_length=255)
    position = models.CharField(max_length=100)
    from_date = models.DateField()
    to_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)
    added_date=models.DateField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.emp_id} - {self.organization}"


class Education(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    degree = models.CharField(max_length=255)
    institution = models.CharField(max_length=255)
    year_of_passing = models.IntegerField()
    grade = models.CharField(max_length=50, blank=True)
    added_date = models.DateField(auto_now=True)
    history = HistoricalRecords()
    def __str__(self):
        return f"{self.emp_id} - {self.degree}"


class Document(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    document_type = models.CharField(max_length=100)
    document_name = models.CharField(max_length=255)
    document_file = models.FileField(upload_to='employee_documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.emp_id} - {self.document_type}"


class LeaveHalfDay(models.Model):
    """
    This model links a half-day entry to a specific leave record and allows tracking of the date and type of half-day.
    """
    half_day_type = models.ForeignKey(HalfDayTypeMaster, on_delete=models.CASCADE)  # Link to half-day type
    half_day_date = models.DateField()  # The date of the half-day
    history = HistoricalRecords()

    def __str__(self):
        return f"Half Day Type: {self.half_day_type.type_name} on {self.half_day_date}"

class LeaveRecord(models.Model):

    emp_id = models.ForeignKey('emp_registers', on_delete=models.DO_NOTHING)
    start_date = models.DateField(null=False)
    end_date = models.DateField(null=False, default=date(2025, 3, 27))
    no_of_days = models.FloatField(default=0.0)
    history = HistoricalRecords()

    # ForeignKeys instead of choices
    leave_type = models.ForeignKey(LeaveTypeMaster, on_delete=models.SET_NULL, null=True)


    approval_status = models.ForeignKey(LeaveStatusMaster, on_delete=models.SET_NULL, null=True, default=None)
    approve_reason=models.TextField(null=True)
    reason = models.TextField()
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    compensatory_leave=models.BooleanField(default=False)
    compensatory_leave_reason=models.TextField(null =True )
    document = models.FileField(upload_to='leave_documents/',null=True)
    half_day = models.ManyToManyField(LeaveHalfDay, blank=True)

    # def __str__(self):
    #     return f"{self.emp_id.name} - {self.leave_type} - {self.approval_status}"


    def __str__(self):
        if self.emp_id:
            return f"{self.emp_id.name} - {self.leave_type} - {self.approval_status}"
        else:
            return f"Leave Record (No Employee) - {self.leave_type} - {self.approval_status}"


#
# class LeaveHalfDay(models.Model):
#     """
#     This model links a half-day entry to a specific leave record and allows tracking of the date and type of half-day.
#     """
#     leave_record = models.ForeignKey(LeaveRecord, related_name='half_day_entries', on_delete=models.CASCADE)
#     half_day_type = models.ForeignKey(HalfDayTypeMaster, on_delete=models.CASCADE)  # Link to half-day type
#     half_day_date = models.DateField()  # The date of the half-day
#
#     def __str__(self):
#         return f"Leave ID: {self.leave_record.id} - Half Day Type: {self.half_day_type.type_name} on {self.half_day_date}"




from django import forms

class EmployeeForm(forms.ModelForm):
    class Meta:
        model = emp_registers
        fields = '__all__'



# class TimesheetAttachmentModel(models.Model):
#     attachment = models.ImageField(upload_to='attachments/')  # your file
#     start_date = models.DateField()
#     end_date = models.DateField()
#     emp_id=models.ForeignKey(emp_registers)
#
#     def __str__(self):
#         return f"Attachment {self.id}"

class Timesheet(models.Model):
    emp_id = models.ForeignKey('emp_registers', on_delete=models.DO_NOTHING)
    pname = models.ForeignKey('Project', on_delete=models.DO_NOTHING)
    task = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    description = models.TextField(null=True)
    attachment = models.ImageField(upload_to='attachments/')
    upload_on=models.DateField(null=True)
    def __str__(self):
        return f"{self.emp_id} - {self.pname} - {self.date}"





class Holiday(models.Model):
    name = models.CharField(max_length=100)
    date = models.DateField()
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.name} ({self.date})"


class Attendance(models.Model):
    emp_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)
    date = models.DateField()
    login_time = models.TimeField(null=True, blank=True)
    logout_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.emp_id.name} - {self.date}"





    class Meta:
        unique_together = ('date', 'emp_id')

    def __str__(self):
        return f"{self.emp_id.emp_id} - {self.date} ({self.half_day_type.name})"


from django.db import models
from django.contrib.auth.models import User
from django.db import models

class ResignationStatusMaster(models.Model):
    status_name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.status_name
from django import forms



class Resignation(models.Model):
    """Base resignation form info."""
    employee = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    resign_date = models.DateField()
    last_date = models.DateField()
    reason = models.TextField()
    selected_elsewhere = models.BooleanField(default=False)
    bond_over = models.BooleanField(default=False)
    advance_salary = models.BooleanField(default=False)
    dues_pending = models.BooleanField(default=False)
    resign_status =models.ForeignKey(ResignationStatusMaster,on_delete=models.DO_NOTHING)

    def __str__(self):
        return f"Resignation of {self.employee.username}"

class ResignStatusAction(models.Model):
    """Tracks status changes for a resignation."""
    resignation = models.ForeignKey(Resignation, on_delete=models.CASCADE, related_name='status_actions')
    action = models.CharField(max_length=255)  # e.g., 'Submitted', 'Approved by Manager', 'HR Review', etc.
    action_by = models.ForeignKey(emp_registers, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='resign_actions')
    action_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.resignation.employee.username} - {self.action} on {self.action_date.strftime('%Y-%m-%d')}"




class ActionChecklist(models.Model):
    """Each checkbox field as a separate boolean column."""
    resignation = models.OneToOneField(Resignation, on_delete=models.CASCADE, related_name='checklist')

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

    def __str__(self):
        return f"Checklist for {self.resignation.employee.username}"



class SentEmail(models.Model):
    employee = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)  # Prevent cascade delete
    recipient_email = models.EmailField()
    subject = models.CharField(max_length=255)
    message_body = models.TextField()  # stores HTML including tags
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.recipient_email} by {self.employee} on {self.sent_at.strftime('%Y-%m-%d')}"
