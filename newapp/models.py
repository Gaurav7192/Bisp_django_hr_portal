from enum import unique

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

# Create your models here.
class logins(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    remember_me = models.BooleanField(default=False)


    def __str__(self):
        return self.email
class registers(models.Model):
    rname=models.CharField(max_length=100,null=False)
    remail=models.EmailField(unique=True,null=False)
    rpassword=models.CharField(max_length=128,null=False)
    admin=models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.rpassword = make_password(self.rpassword)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.remail


class registers_v2(models.Model):
    rname = models.CharField(max_length=100, null=False)
    remail = models.EmailField(unique=True, null=False)
    rpassword = models.CharField(max_length=128, null=False)
    admin = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.rpassword = make_password(self.rpassword)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.remail
