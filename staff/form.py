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

# class EmployeeForm(forms.ModelForm):
#     # Basic Information
#     name = models.CharField(max_length=100, null=False)
#     email = models.EmailField(unique=True, null=False)
#     password = models.CharField(max_length=128, null=False)
#
#     # Role & Department
#     position = models.CharField(max_length=10, choices=ROLE_CHOICES, null=True)
#     department = models.CharField(max_length=100, blank=True, null=True)
#
#     # Date Fields
#     registration_date = models.DateTimeField(auto_now_add=True)
#     joindate = models.DateField(null=True)
#
#     # Reporting & Personal Details
#     reportto = models.CharField(max_length=100, null=False)
#     gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True)
#     marriage_status = models.CharField(max_length=20, null=True)
#     aadhar_no = models.CharField(max_length=12, unique=True, null=True)
#     dob = models.DateField(null=True)
#     nationality = models.CharField(max_length=30, null=True)
#     religion = models.CharField(max_length=30, null=True)
#
#     # Additional Meta Information
#     class Meta:
#         model = emp_registers
#         fields = '__all__'
#
#     def __str__(self):
#         return f"{self.name} - {self.position}"


class EmployeeForm(forms.ModelForm):
    class Meta:
        model = emp_registers
        fields = [
            'name', 'email', 'password', 'position', 'department',
            'joindate', 'reportto', 'gender', 'marriage_status',
            'aadhar_no', 'dob', 'nationality', 'religion','profile_pic'
        ]

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Email'}),
            'password': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password'}),
            'position': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Department'}),
            'joindate': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'reportto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Reporting Manager'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'marriage_status': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Marriage Status'}),
            'aadhar_no': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Aadhar Number'}),
            'dob': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'nationality': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Nationality'}),
            'religion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Religion'}),
            'profile_pic': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if emp_registers.objects.exclude(id=self.instance.id).filter(email=email).exists():
            raise forms.ValidationError("This email is already used by another employee.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        rpassword = cleaned_data.get('rpassword')
        position = cleaned_data.get('position')
        department = cleaned_data.get('department')
        joindate = cleaned_data.get('joindate')
        reportto = cleaned_data.get('reportto')
        gender = cleaned_data.get('gender')
        marriage_status = cleaned_data.get('marriage_status')
        aadhar_no = cleaned_data.get('aadhar_no')
        dob = cleaned_data.get('dob')
        nationality = cleaned_data.get('nationality')
        religion = cleaned_data.get('religion')

        if name:
            if not re.match(r'^[a-zA-Z ]+$', name):
                self.add_error('name', 'Invalid name. Only letters and spaces are allowed.')
            if name.startswith(' '):
                self.add_error('name', 'Name should not start with a space.')
        if email:
            if emp_registers.objects.exclude(id=self.instance.id).filter(email=email).exists():
                self.add_error('email', "This email is already used by another employee.")
            if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                self.add_error('email', 'Invalid email address.')
        if password:
            if len(password) < 8 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]',
                                                                                       password) or not re.search(
                    r'[!@#$%^&*]', password):
                self.add_error('password',
                               'Password must be at least 8 characters, including one uppercase letter, one number, and one special character.')
        if dob:
            if dob >= datetime.today().date():
                self.add_error('dob', 'Invalid Date of Birth.')
            if dob < date(1980, 1, 1):
                self.add_error('dob', 'date of birth not more than 1980.')
            if dob > datetime.today().date() - timedelta(days=18 * 365):
                self.add_error('dob', 'Staff must be at least 18 years old.')
        if joindate:
            if joindate < datetime(2025, 1, 1).date():
                self.add_error('joindate', 'Joining date cannot be before January 1, 2025.')
        if aadhar_no:
            if emp_registers.objects.exclude(id=self.instance.id).filter(aadhar_no=aadhar_no).exists():
                self.add_error('aadhar_no', "This Aadhar number is already used by another employee.")
            if not re.match(r'^\d{12}$', aadhar_no):
                self.add_error('aadhar_no', 'Invalid Aadhar number. It must be 12 digits.')
        return cleaned_data
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.password = instance.password
        if commit:
            instance.save()
        return instance


class LoginForm(forms.Form):
    email = forms.CharField(label="email", max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    remember_me = forms.BooleanField(initial=False)


