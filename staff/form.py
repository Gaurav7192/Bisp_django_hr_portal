from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from .models import *
from django import forms
import re
# Role choices
ROLE_CHOICES = [
    ('HR', 'HR'),
    ('Manager', 'Manager'),
    ('Staff', 'Staff'),
]

# Gender choices
GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
]




from django.contrib.auth.hashers import check_password

class EmployeeForm(forms.ModelForm):
    # Dropdown for Position (Foreign Key)
    position = forms.ModelChoiceField(
        queryset=RoleMaster.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    # Dropdown for Department (Foreign Key)
    department = forms.ModelChoiceField(
        queryset=DepartmentMaster.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )

    # Dropdown for Reporting Manager (only non-Staff)
    # Generate dropdown with employee names
    reportto = forms.ModelChoiceField(
        queryset=emp_registers.objects.exclude(position__role__iexact='Employee'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = emp_registers
        fields = [
            'name', 'email', 'password', 'position', 'department',
            'joindate', 'reportto', 'salary','designation'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Email'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password'}),
            'joindate': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'salary': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Salary'}),
        }
        salary = forms.DecimalField(
            max_digits=10,
            decimal_places=2,
            required=True,
            validators=[MinValueValidator(0)]  # Ensures the salary is non-negative
        )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if emp_registers.objects.exclude(id=self.instance.id).filter(email=email).exists():
            raise forms.ValidationError("This email is already used by another employee.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        password = cleaned_data.get('password')
        joindate = cleaned_data.get('joindate')
        salary= cleaned_data.get('salary')

        # Validate name format
        if name and not re.match(r'^[a-zA-Z ]+$', name):
            self.add_error('name', 'Invalid name. Only letters and spaces are allowed.')

        # Password strength validation
        if password:
            if (
                len(password) < 8 or
                not re.search(r'[A-Z]', password) or
                not re.search(r'[0-9]', password) or
                not re.search(r'[!@#$%^&*]', password)
            ):
                self.add_error('password', 'Password must be at least 8 characters, including one uppercase letter, one number, and one special character.')

        # Join date check
        if joindate and joindate < datetime(2025, 1, 1).date():
            self.add_error('joindate', 'Joining date cannot be before January 1, 2025.')


        if salary and float(salary) < 0 :
            print("xaskdhscvsdv cbsdb ",salary)
            self.add_error('salary', 'Salary cannot be negative')
            return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.password = instance.password  # Note: Apply hashing elsewhere if needed
        if commit:
            instance.save()
        return instance


from django import forms
from django.utils import timezone
from django.contrib.auth import login as auth_login
from django.conf import settings  # To access settings like LOGIN_ATTEMPT_THRESHOLD

# Assuming emp_registers is in the same app or correctly imported
from .models import emp_registers  # Adjust import path as needed


class LoginForm(forms.Form):
    email = forms.CharField(label="Email", max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    remember_me = forms.BooleanField(initial=False, required=False)  # Make remember_me not required

    # Store the authenticated user if valid, so the view can access it
    user_cache = None

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        # Define lockout settings (you can also put these in settings.py)
        LOGIN_ATTEMPT_THRESHOLD = getattr(settings, 'LOGIN_ATTEMPT_THRESHOLD', 5)
        LOCKOUT_DURATION_HOURS = getattr(settings, 'LOCKOUT_DURATION_HOURS', 2)

        # 1. Basic email existence check
        if not email:
            self.add_error('email', 'Email field is required.')
            raise forms.ValidationError("Email not provided.")  # Stop further processing for missing email

        try:
            user = emp_registers.objects.get(email=email)
        except emp_registers.DoesNotExist:
            # Important: Give a generic error to avoid exposing if email exists
            self.add_error('email', 'Invalid email or password.')
            # If email doesn't exist, we don't have a user object to track attempts
            raise forms.ValidationError("Invalid credentials.")

        # 2. Check if account is locked
        if user.is_locked():
            remaining_seconds = (user.account_locked_until - timezone.now()).total_seconds()
            hours, remainder = divmod(remaining_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)

            # Format remaining time dynamically
            time_parts = []
            if hours >= 1:
                time_parts.append(f"{int(hours)} hour{'s' if hours > 1 else ''}")
            if minutes >= 1:
                time_parts.append(f"{int(minutes)} minute{'s' if minutes > 1 else ''}")
            if time_parts:
                time_str = " and ".join(time_parts)
            else:
                time_str = "a moment"

            self.add_error('email',
                           f"Account locked due to too many failed attempts. Please try again after {time_str}.")
            raise forms.ValidationError("Account is locked.")  # Stop further processing

        # 3. Check password
        if not password:
            self.add_error('password', 'Password field is required.')
            raise forms.ValidationError("Password not provided.")  # Stop further processing for missing password

        if user.check_password(password):
            # Password is correct!
            if user.failed_login_attempts > 0 or user.account_locked_until:
                user.unlock_account()  # Reset attempts if they were non-zero
            self.user_cache = user  # Store the authenticated user for the view
        else:
            # Password is incorrect
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= LOGIN_ATTEMPT_THRESHOLD:
                user.lock_account(duration_hours=LOCKOUT_DURATION_HOURS)
                self.add_error('password',
                               f"Too many failed attempts. Account locked for {LOCKOUT_DURATION_HOURS} hours.")
            else:
                # Generic error for invalid password
                self.add_error('password', 'Invalid email or password.')

            user.save()  # Save the updated failed_login_attempts or lockout status
            raise forms.ValidationError("Invalid credentials.")  # Mark the form as invalid

        return cleaned_data
class ExitEmailForm(forms.Form):
    to = forms.EmailField(label='To', required=True)
    cc = forms.CharField(label='CC', required=False)
    bcc = forms.CharField(label='BCC', required=False)
    subject = forms.CharField(label='Subject', required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)
    attachment = forms.FileField(required=False)