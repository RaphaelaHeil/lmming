# Generated by Django 5.1.4 on 2025-02-06 09:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0029_externalrecord_endyear_externalrecord_recordid_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='externalrecord',
            old_name='recordId',
            new_name='arabRecordId',
        ),
    ]
