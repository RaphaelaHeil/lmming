# Generated by Django 5.0.4 on 2024-09-04 07:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0019_alter_processingstep_processingsteptype'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalrecord',
            name='coverage',
            field=models.CharField(blank=True, default=''),
        ),
    ]
