# Generated by Django 5.2.1 on 2025-06-23 06:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0050_latestpayslip'),
    ]

    operations = [
        migrations.AddField(
            model_name='latestpayslip',
            name='file',
            field=models.FileField(null=True, upload_to='payslip/'),
        ),
    ]
