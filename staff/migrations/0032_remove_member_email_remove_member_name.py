# Generated by Django 5.1.7 on 2025-05-20 05:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0031_timesheet_upload_on'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='member',
            name='email',
        ),
        migrations.RemoveField(
            model_name='member',
            name='name',
        ),
    ]
