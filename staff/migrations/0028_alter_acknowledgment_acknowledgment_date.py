# Generated by Django 5.1.7 on 2025-05-14 10:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('staff', '0027_handbook_document_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='acknowledgment',
            name='acknowledgment_date',
            field=models.DateField(null=True),
        ),
    ]
