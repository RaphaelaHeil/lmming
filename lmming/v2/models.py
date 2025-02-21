from django.db.models import Model, CharField, TextField, ForeignKey, TextChoices, CASCADE, URLField, UniqueConstraint
from django.contrib.postgres.fields import ArrayField


class MetadataValueType(TextChoices):
    PLAINTEXT = "PLAINTEXT"
    URL = "URL"
    DATE = "DATE"
    PLAIN_HANDLE = "PLAIN HANDLE"
    LOCATION_HANDLE = "LOCATION HANDLE"


class Level(TextChoices):
    item = "ITEM"
    page = "PAGE"


class ProcessingStepMode(TextChoices):
    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"


class Vocabulary(Model):
    name = CharField(blank=False, unique=True)
    description = TextField(blank=True)
    url = URLField(blank=True)


class MetadataTerm(Model):
    description = TextField(blank=True)
    standardTerm = CharField()
    vocabulary = ForeignKey(Vocabulary, on_delete=CASCADE)

    class Meta:
        constraints = [UniqueConstraint(fields=["vocabulary", "standardTerm"], name="vocabulary-unique-standardTerm")]


class Project(Model):
    name = CharField()
    abbreviation = CharField(max_length=6)
    description = TextField(blank=True)
    recordIdColumnName = CharField(blank=True)
    externalRecordColumnNames = ArrayField(CharField(), blank=list)
