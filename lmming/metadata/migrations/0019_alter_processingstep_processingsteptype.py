# Generated by Django 5.0.4 on 2024-07-18 14:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('metadata', '0018_alter_processingstep_processingsteptype'),
    ]

    operations = [
        migrations.AlterField(
            model_name='processingstep',
            name='processingStepType',
            field=models.CharField(choices=[('FILENAME', 'Filename-based extraction'), ('FILEMAKER_LOOKUP', 'Lookup in Filemaker export'), ('GENERATE', 'Generate/Calculate'), ('FAC_MANUAL', 'Manual'), ('IMAGE', 'Image-based extraction'), ('NER', 'Named Entity Recognition'), ('MINT_ARKS', 'Mint ARKs'), ('ARAB_GENERATE', 'Generate/Calculate'), ('ARAB_MANUAL', 'Manual'), ('ARAB_MINT_HANDLE', 'Mint Handle IDs')]),
        ),
    ]