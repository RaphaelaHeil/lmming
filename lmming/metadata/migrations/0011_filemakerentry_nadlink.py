# Generated by Django 5.0.4 on 2024-06-11 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0010_delete_urlsettings_report_noid_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='filemakerentry',
            name='nadLink',
            field=models.URLField(blank=True, default=''),
        ),
    ]
