# Generated by Django 5.1.7 on 2025-04-12 10:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0005_halfdaymaster'),
    ]

    operations = [
        migrations.AlterField(
            model_name='holiday',
            name='date',
            field=models.DateField(),
        ),
    ]
