from enum import unique
from datetime import datetime
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from datetime import date,datetime,time,timedelta
from django.db.models import JSONField, DO_NOTHING
import logging
from datetime import timedelta
from django.utils import timezone
logger = logging.getLogger(__name__)
from django.utils.timezone import now
from simple_history.models import HistoricalRecords
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError

from .  import vector_store, query_engine, document_processor

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
    name = models.CharField(max_length=100, null=False)
    email = models.EmailField(unique=True, null=False)
    password = models.CharField(max_length=128, null=False)

    position = models.ForeignKey(RoleMaster, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(DepartmentMaster, on_delete=models.SET_NULL, null=True)
    designation = models.ForeignKey(DesignationMaster, on_delete=models.SET_NULL, null=True, blank=True)

    registration_date = models.DateTimeField(auto_now_add=True, )
    joindate = models.DateField(null=True)
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

    def process_for_chatbot(self):
        """
        Extracts text from the document and adds it to the FAISS vector index.
        """
        try:
            index = load_or_create_index()
            file_path = self.document.path
            chunks = document_processor.extract_chunks(file_path)
            vector_store.add_text_chunks(index, chunks)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to process handbook: {e}")
            return False


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
    phone_number = models.CharField(max_length=10 ,null=True)
    guidance_phone_number = models.CharField(max_length=10 ,null=True)
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


class LatestPayslip(models.Model):
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to='payslip/',null=True)

    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name



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
class TodoTask(models.Model):
    name = models.CharField(max_length=255)
    emp_id = models.ForeignKey('emp_registers', on_delete=DO_NOTHING,null=True ,blank =True )
    badge = models.CharField(max_length=20, choices=[
        ('success', 'Success'),
        ('danger', 'Danger'),
        ('secondary', 'Secondary'),
    ])
    datetime = models.DateTimeField()  # Stores full datetime (for filtering)

    def hour(self):
        return self.datetime.hour

    def date_only(self):
        return self.datetime.date()

class Payslip(models.Model):
    pass
    employee_name = models.CharField(max_length=255)
    employee_id = models.ForeignKey(emp_registers, on_delete=models.DO_NOTHING)
    department = models.CharField(max_length=255, blank=True, null=True)
    month = models.CharField(max_length=50)  # e.g., "June 2025" or "06-2025"


    # Earnings
    SALARY_BASIC = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    SALARY_HRA = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    SALARY_DA = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)

    GROSS_BASIC = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    GROSS_HRA = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    GROSS_DA = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    CONVENCE_ALLOWANCE = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True,
                                            blank=True)

    SPECIAL_ALLOWNCES = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True,
                                            blank=True)
    Project_Incentive = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True,
                                            blank=True)
    Variable_Pay = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)

    GROSS_TOTAL = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)

    # Deductions
    ESI = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    PF = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    Salary_Advance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True,
                                         blank=True)
    Negative_Leave = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True,
                                         blank=True)
    TDS = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)

    Total_Deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True,
                                           blank=True)


    # Legacy compatibility
    basic = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    hra = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    allowance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    from django.core.validators import MinValueValidator

    # Add these to your model (anywhere within the class)


    PRESENT_DAYS = models.IntegerField(default=0, null=True, blank=True, validators=[MinValueValidator(0)])
    PAID_LEAVE = models.IntegerField(default=0, null=True, blank=True, validators=[MinValueValidator(0)])
    WEEK_OFF = models.IntegerField(default=0, null=True, blank=True, validators=[MinValueValidator(0)])
    UNPAID_LEAVE = models.IntegerField(default=0, null=True, blank=True, validators=[MinValueValidator(0)])
    WORKING_DAYS = models.IntegerField(default=0, null=True, blank=True, validators=[MinValueValidator(0)])

    TOTAL_SALARY = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), null=True, blank=True)


    class Meta:
        unique_together = ('employee_id', 'month')
        verbose_name = "Payslip Record"
        verbose_name_plural = "Payslip Records"

    def __str__(self):
        return f"{self.employee_name} ({self.employee_id}) - {self.month} Payslip"

    def save(self, *args, **kwargs):
        # Total earnings (gross)
        self.GROSS_TOTAL = (
                self.GROSS_BASIC + self.GROSS_HRA + self.GROSS_DA +
                self.CONVENCE_ALLOWANCE + self.SPECIAL_ALLOWNCES +
                self.Project_Incentive + self.Variable_Pay
        )

        # Total deductions
        self.Total_Deductions = (
                self.ESI + self.PF + self.Salary_Advance +
                self.Negative_Leave + self.TDS
        )

        # Net salary = gross - deductions
        self.NET_SALARY = self.GROSS_TOTAL - self.Total_Deductions

        # Optional: Total salary = basic + hra + da
        self.TOTAL_SALARY = (
                self.SALARY_BASIC + self.SALARY_HRA + self.SALARY_DA
        )

        # Keep legacy fields in sync
        self.basic = self.SALARY_BASIC
        self.hra = self.SALARY_HRA
        self.allowance = self.SPECIAL_ALLOWNCES + self.CONVENCE_ALLOWANCE + self.Variable_Pay
        self.deductions = self.Total_Deductions
        self.net_salary = self.NET_SALARY

        super().save(*args, **kwargs)

    def clean(self):
        salary_fields = [
            'SALARY_BASIC', 'SALARY_HRA', 'SALARY_DA',
            'GROSS_BASIC', 'GROSS_HRA', 'GROSS_DA',
            'CONVENCE_ALLOWANCE', 'SPECIAL_ALLOWNCES',
            'Project_Incentive', 'Variable_Pay',
            'ESI', 'PF', 'Salary_Advance', 'Negative_Leave', 'TDS',
        ]

        for field in salary_fields:
            value = getattr(self, field)
            if value < 0:
                raise ValidationError({field: f"{field.replace('_', ' ')} cannot be negative."})



class toda_task(models.Model):
    user = models.ForeignKey('emp_registers', on_delete=models.CASCADE, related_name='tasks')
    desc = models.TextField()
    badge = models.CharField(max_length=20, default='success')
    datetime = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} - {self.desc} at {self.datetime}"


from django.db import models

# Assuming you have other models in your staff app, add this new one
class HRPolicy(models.Model):
    title = models.CharField(max_length=255, unique=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "HR Policy"
        verbose_name_plural = "HR Policies"
        ordering = ['title'] # Order policies by title by default

    def __str__(self):
        return self.title
class ChatLog(models.Model):
    emp_id = models.ForeignKey(emp_registers, to_field='id', on_delete=models.CASCADE)
    message = models.TextField()
    sender = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp}] {self.emp_id.emp_id} - {self.sender}: {self.message}"

    @staticmethod
    def get_recent_chats(emp_id):
        week_ago = now() - timedelta(days=7)
        return ChatLog.objects.filter(emp_id__emp_id=emp_id, timestamp__gte=week_ago).order_by('timestamp')

# ... potentially other models you already have ...


# profiles/models.py

from django.db import models
import json # Import json for serialization/deserialization
class UserProfile(models.Model):
    """
    Main UserProfile model, now linked to EmpRegister.
    Skills, projects, experience, and ratings are stored as JSON strings.
    """
    # Foreign Key to EmpRegister
    emp_register = models.ForeignKey(
        emp_registers,
        on_delete=models.CASCADE, # If an EmpRegister is deleted, delete associated UserProfiles

    )

    name = models.CharField(max_length=255, help_text="Full name of the user/employee")
    role = models.ForeignKey(
        DesignationMaster,  # model reference
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Role or designation of the user"
    )
    # Storing lists of dictionaries as JSON strings in TextField
    skills_json = models.TextField(default="[]", blank=True, help_text="JSON array of skills")
    projects_json = models.TextField(default="[]", blank=True, help_text="JSON array of projects")
    experiences_json = models.TextField(default="[]", blank=True, help_text="JSON array of experiences")
    ratings_json = models.TextField(default="[]", blank=True, help_text="JSON array of ratings")

    created_at = models.DateTimeField(auto_now_add=True)

    def set_skills(self, data):
        self.skills_json = json.dumps(data)

    def get_skills(self):
        return json.loads(self.skills_json)

    def set_projects(self, data):
        self.projects_json = json.dumps(data)

    def get_projects(self):
        return json.loads(self.projects_json)

    def set_experiences(self, data):
        self.experiences_json = json.dumps(data)

    def get_experiences(self):
        return json.loads(self.experiences_json)

    def set_ratings(self, data):
        self.ratings_json = json.dumps(data)

    def get_ratings(self):
        return json.loads(self.ratings_json)

    def __str__(self):
        return f"{self.name} (Linked to {self.emp_register.employee_id})"

class SkillRecommendation(models.Model):
    employee = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    recommended_skills = models.TextField()
    top_peer_ids = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

class Feedback(models.Model):
    employee = models.ForeignKey(emp_registers, on_delete=models.CASCADE)
    skill = models.CharField(max_length=255)
    feedback_type = models.CharField(max_length=50)  # accepted, rejected, already_known, etc.
    timestamp = models.DateTimeField(auto_now_add=True)



