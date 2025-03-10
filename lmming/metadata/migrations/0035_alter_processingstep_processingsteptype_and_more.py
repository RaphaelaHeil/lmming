# Generated by Django 5.1.4 on 2025-02-28 12:01

import django.contrib.postgres.fields
from django.db import migrations, models

def migrateFormatCharToArray(apps, schema_editor):
    MyModel = apps.get_model('metadata', 'Report')

    for mm in MyModel.objects.all():
        if "format_old" in mm.__dict__:
            oldFormat = mm.format_old
            newFormat = [oldFormat]
            mm.format_new = newFormat
            mm.save()
        else:
            print(mm)

def migrateMediumCharToArray(apps, schema_editor):
    MyModel = apps.get_model('metadata', 'Report')

    for mm in MyModel.objects.all():
        oldFormat = mm.medium_old
        newFormat = [oldFormat]
        mm.medium_new = newFormat
        mm.save()


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0034_alter_processingstep_processingsteptype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processingstep',
            name='processingStepType',
            field=models.CharField(choices=[('FILENAME', 'Filename-based extraction'), ('FILEMAKER_LOOKUP', 'Lookup in Filemaker export'), ('GENERATE', 'Generate/Calculate'), ('FAC_MANUAL', 'Manual'), ('IMAGE', 'Image-based extraction'), ('NER', 'Named Entity Recognition'), ('MINT_ARKS', 'Mint ARKs'), ('ARAB_GENERATE', 'Generate/Calculate'), ('ARAB_MANUAL', 'Manual'), ('ARAB_MINT_HANDLE', 'Mint Handle IDs'), ('ARAB_TRANSLATE_TO_SWEDISH', 'Translate to Swedish'), ('FAC_TRANSLATE_TO_SWEDISH', 'Translate to Swedish'), ('FILEMAKER_LOOKUP_ARAB', 'External record look-up'), ('ARAB_OTHER_MANUAL', 'Manual'), ('ARAB_OTHER_MINT_HANDLE', 'Mint Handle IDs')]),
        ),
        migrations.RenameField(
            model_name='report',
            old_name='format',
            new_name='format_old',
        ),
        migrations.AddField(
            model_name='report',
            name='format_new',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(), blank=True, default=list, null=True, size=None),
        ),
        migrations.RunPython(migrateFormatCharToArray),
        migrations.RemoveField(
            model_name='report',
            name='format_old',
        ),
        migrations.RenameField(
            model_name='report',
            old_name='format_new',
            new_name='format',
        ),
        migrations.RenameField(
            model_name='report',
            old_name='medium',
            new_name='medium_old',
        ),
        migrations.AddField(
            model_name='report',
            name='medium_new',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(), blank=True, default=list,
                                                            null=True, size=None),
        ),
        migrations.RunPython(migrateFormatCharToArray),
        migrations.RemoveField(
            model_name='report',
            name='medium_old',
        ),
        migrations.RenameField(
            model_name='report',
            old_name='medium_new',
            new_name='medium',
        ),
    ]
