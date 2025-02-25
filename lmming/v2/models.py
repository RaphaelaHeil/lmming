from django.contrib.postgres.fields import ArrayField
from django.db.models import Model, CharField, TextField, ForeignKey, TextChoices, CASCADE, URLField, UniqueConstraint, \
    BooleanField, DateField, PositiveIntegerField, JSONField


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
    prefix = CharField(blank=False, default="prefix")

    def __str__(self):
        return f"{self.name} ({self.prefix})"


class MetadataTerm(Model):
    description = TextField(blank=True)
    standardTerm = CharField()
    vocabulary = ForeignKey(Vocabulary, on_delete=CASCADE)

    class Meta:
        constraints = [UniqueConstraint(fields=["vocabulary", "standardTerm"], name="vocabulary-unique-standardTerm")]

    def __str__(self):
        return f"{self.standardTerm} ({self.vocabulary.name})"


class Project(Model):
    name = CharField()
    abbreviation = CharField(max_length=6)
    description = TextField(blank=True)
    recordIdColumnName = CharField(blank=True)
    externalRecordColumnNames = ArrayField(CharField(), blank=list)
    prefixSeparator = CharField(blank=False, default=".")

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"


class BasicValueType(Model):
    valueTypes = ArrayField(CharField(choices=MetadataValueType.choices), default=list, )
    multiple = BooleanField()
    range = BooleanField()

    def __str__(self):
        return ",".join(self.valueTypes) + (" multiple" if self.multiple else "") + (" range" if self.range else "")


class ChoiceValueType(BasicValueType):
    options = ArrayField(CharField(), default=list, )

    def __str__(self):
        return str(self.options) + (" multiple" if self.multiple else "") + (" range" if self.range else "")


class ProjectMetadataTerm(Model):
    project = ForeignKey(Project, on_delete=CASCADE)
    metadataTerm = ForeignKey(MetadataTerm, on_delete=CASCADE)
    mandatory = BooleanField()
    level = CharField(choices=Level.choices)
    valueType = ForeignKey(BasicValueType, on_delete=CASCADE)

    def __str__(self):
        return f"{self.project.name} - {self.metadataTerm.standardTerm} ({self.level}, {self.mandatory})"


class ExternalRecordEntry(Model):
    recordId = CharField()
    project = ForeignKey(Project, on_delete=CASCADE)
    startDate = DateField(blank=True, null=True)
    endDate = DateField(blank=True, null=True)

    def __str__(self):
        base = f"{self.recordId} - {self.project.name}"
        dateString = ""
        if self.startDate or self.endDate:
            dateString = " -- ".join(
                [str(self.startDate) if self.startDate else "", str(self.endDate) if self.endDate else ""])
        return base + (f" ({dateString})" if dateString else "")


class ExternalRecordField(Model):
    key = CharField()
    value = CharField(blank=True)
    externalRecord = ForeignKey(ExternalRecordEntry, on_delete=CASCADE)

    def __str__(self):
        return (f"{self.externalRecord.project.abbreviation}: {self.externalRecord.recordId} - {self.key}: "
                f"{self.value if self.value else ''}")


class ProcessingStepConfiguration(Model):
    order = PositiveIntegerField()
    key = CharField()
    description = CharField(blank=True, default="")
    options = JSONField(default=dict, blank=True)
    project = ForeignKey(Project, on_delete=CASCADE)
