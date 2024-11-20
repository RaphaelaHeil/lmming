# Generated by Django 5.1.1 on 2024-11-14 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0022_alter_processingstep_processingsteptype_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='defaultnumbersettings',
            name='name',
            field=models.CharField(choices=[('AVAILABLE_YEAR_OFFSET', 'Number of years, calculated from date of publication, until the material becomes available'), ('NER_NORMALISATION_END_YEAR', 'Year after which the transcriptions should not be normalised anymore (given year is the final yearthat will be normalised)')], primary_key=True, serialize=False),
        ),
    ]