# Generated by Django 5.0.4 on 2024-07-10 08:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0015_alter_processingstep_processingsteptype'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='filemakerentry',
            name='id',
        ),
        migrations.AlterField(
            model_name='filemakerentry',
            name='archiveId',
            field=models.CharField(primary_key=True, serialize=False),
        ),
    ]