# Generated by Django 5.1.7 on 2025-04-12 05:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0003_remove_leavetypemaster_created_on'),
    ]

    operations = [
        migrations.AddField(
            model_name='leaverecord',
            name='approve_reason',
            field=models.TextField(null=True),
        ),
    ]
