# Generated by Django 5.1.1 on 2024-11-22 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0024_extractiontransfer_lastupdated'),
    ]

    operations = [
        migrations.AddField(
            model_name='job',
            name='lastUpdated',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]