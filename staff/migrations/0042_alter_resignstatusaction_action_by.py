# Generated by Django 5.1.7 on 2025-05-23 13:12

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0041_resignationstatusmaster_resignation_actionchecklist_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resignstatusaction',
            name='action_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resign_actions', to='staff.emp_registers'),
        ),
    ]
