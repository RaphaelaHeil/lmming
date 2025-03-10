# Generated by Django 5.1.4 on 2025-02-27 20:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0033_report_comment_report_format_report_medium_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processingstep',
            name='processingStepType',
            field=models.CharField(choices=[('FILENAME', 'Filename-based extraction'), ('FILEMAKER_LOOKUP', 'Lookup in Filemaker export'), ('GENERATE', 'Generate/Calculate'), ('FAC_MANUAL', 'Manual'), ('IMAGE', 'Image-based extraction'), ('NER', 'Named Entity Recognition'), ('MINT_ARKS', 'Mint ARKs'), ('ARAB_GENERATE', 'Generate/Calculate'), ('ARAB_MANUAL', 'Manual'), ('ARAB_MINT_HANDLE', 'Mint Handle IDs'), ('ARAB_TRANSLATE_TO_SWEDISH', 'Translate to Swedish'), ('FAC_TRANSLATE_TO_SWEDISH', 'Translate to Swedish'), ('FILEMAKER_LOOKUP_ARAB', 'External record look-up'), ('ARAB_OTHER_GENERATE', 'Generate'), ('ARAB_OTHER_MANUAL', 'Manual'), ('ARAB_OTHER_MINT_HANDLE', 'Mint Handle IDs')]),
        ),
    ]
