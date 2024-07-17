# Generated by Django 5.0.4 on 2024-07-17 13:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0016_remove_filemakerentry_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalRecord',
            fields=[
                ('archiveId', models.CharField(primary_key=True, serialize=False)),
                ('organisationName', models.CharField()),
                ('county', models.CharField(blank=True, default='')),
                ('municipality', models.CharField(blank=True, default='')),
                ('city', models.CharField(blank=True, default='')),
                ('parish', models.CharField(blank=True, default='')),
                ('catalogueLink', models.URLField(blank=True, default='')),
            ],
        ),
        migrations.DeleteModel(
            name='FilemakerEntry',
        ),
    ]