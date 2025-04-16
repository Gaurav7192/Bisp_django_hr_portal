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
        queryset=emp_registers.objects.exclude(position__role__iexact='Staff'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )

    class Meta:
        model = emp_registers
        fields = [
            'name', 'email', 'password', 'position', 'department',
            'joindate', 'reportto', 'salary'
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

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.password = instance.password  # Note: Apply hashing elsewhere if needed
        if commit:
            instance.save()
        return instance


class LoginForm(forms.Form):
    email = forms.CharField(label="email", max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="Password", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    remember_me = forms.BooleanField(initial=False)


