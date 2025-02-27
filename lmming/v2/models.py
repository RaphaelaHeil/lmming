from django.contrib.postgres.fields import ArrayField
from django.db.models import Model, CharField, TextField, ForeignKey, TextChoices, CASCADE, URLField, UniqueConstraint, \
    BooleanField, DateField, PositiveIntegerField, JSONField, FileField, OneToOneField, DateTimeField
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


class MetadataValueType(TextChoices):
    PLAINTEXT = "PLAINTEXT"
    URL = "URL"
    DATE = "DATE"
    PLAIN_HANDLE = "PLAIN HANDLE"
    LOCATION_HANDLE = "LOCATION HANDLE"
    IIIF_HANDLE = "IIIF_HANDLE"
    FIXED_VALUE = "FIXED_VALUE"


class Level(TextChoices):
    item = "ITEM"
    page = "PAGE"


class ProcessingStepMode(TextChoices):
    AUTOMATIC = "AUTOMATIC"
    MANUAL = "MANUAL"


class FileType(TextChoices):
    IMAGE = "IMAGE"
    PDF = "PDF"
    XML = "XML"
    PLAINTEXT = "PLAINTEXT"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    OTHER = "OTHER"


class Status(TextChoices):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    AWAITING_HUMAN_INPUT = "AWAITING_HUMAN_INPUT"
    AWAITING_HUMAN_VALIDATION = "AWAITING_HUMAN_VALIDATION"


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


class FixedValueType(BasicValueType):
    values = ArrayField(CharField(), blank=list)

    def __str__(self):
        return str(self.values) + (" multiple" if self.multiple else "") + (" range" if self.range else "")


class ProjectMetadataTerm(Model):
    project = ForeignKey(Project, on_delete=CASCADE)
    metadataTerm = ForeignKey(MetadataTerm, on_delete=CASCADE)
    mandatory = BooleanField()
    level = CharField(choices=Level.choices)
    valueType = ForeignKey(BasicValueType, on_delete=CASCADE)
    includeInExport = BooleanField(default=True)

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


class Process(Model):
    name = CharField()
    project = ForeignKey(Project, on_delete=CASCADE)
    status = CharField(choices=Status.choices, default=Status.PENDING)
    lastModified = DateTimeField(auto_now=True)

    def updateStatus(self):
        jobStatuses = set([step.status for step in self.processingSteps.all()])

        for status in [Status.ERROR, Status.AWAITING_HUMAN_INPUT, Status.AWAITING_HUMAN_VALIDATION]:
            if status in jobStatuses:
                self.status = status
                self.save()
                return

        if len(jobStatuses) == 1:
            self.status = jobStatuses.pop()
            self.save()
            return
        else:
            for status in [Status.QUEUED, Status.IN_PROGRESS]:
                if status in jobStatuses:
                    self.status = status
                    self.save()
                    return
        self.status = Status.PENDING
        self.save()


class Item(Model):
    process = OneToOneField(Process, on_delete=CASCADE, primary_key=True, )
    recordId = CharField(blank=False)
    documentTypeIdentifier = CharField(blank=False)  # type given in the filenames
    date = ArrayField(DateField(), blank=False, null=True)  # date(s) given in the filenames


class Page(Model):
    item = ForeignKey(Item, on_delete=CASCADE)
    originalFilename = CharField(blank=False)
    file = FileField(blank=False)
    fileType = CharField(choices=FileType.choices, default=FileType.OTHER)
    pageNumber = PositiveIntegerField(default=0)


class ProcessingStep(Model):
    configuration = ForeignKey(ProcessingStepConfiguration, on_delete=CASCADE)
    process = ForeignKey(Process, on_delete=CASCADE, related_name="processingSteps")
    status = CharField(choices=Status.choices, default=Status.PENDING)
    log = CharField(blank=True)
    startDate = DateTimeField()
    lastModified = DateTimeField(auto_now=True)
    mode = CharField(choices=ProcessingStepMode.choices, default=ProcessingStepMode.AUTOMATIC)
    humanValidation = BooleanField(default=False)


class MetadataAssignment(Model):
    item = ForeignKey(Item, on_delete=CASCADE, blank=True, null=True)
    page = ForeignKey(Page, on_delete=CASCADE, blank=True, null=True)
    projectMetadataTerm = ForeignKey(ProjectMetadataTerm, on_delete=CASCADE)


class TextValue(Model):
    text = TextField(blank=True)
    metadataAssignment = ForeignKey(MetadataAssignment, on_delete=CASCADE, null=True)


class DateValue(Model):
    date = DateField(blank=True)
    metadataAssignment = ForeignKey(MetadataAssignment, on_delete=CASCADE, null=True)


class PlainHandleValue(Model):
    handle = CharField(blank=True)
    resolveTo = URLField(blank=True)
    noid = CharField(blank=True)
    metadataAssignment = ForeignKey(MetadataAssignment, on_delete=CASCADE, null=True)


class LocationHandleValue(Model):
    handle = CharField(blank=True)
    noid = CharField(blank=True)
    metadataAssignment = ForeignKey(MetadataAssignment, on_delete=CASCADE, null=True)


class Location(Model):
    locationHandle = ForeignKey(LocationHandleValue, on_delete=CASCADE)
    resolveTo = URLField(blank=True)
    view = CharField(blank=True)
    language = CharField(blank=True)
    weight = PositiveIntegerField(default=0)


# noinspection PyUnusedLocal
@receiver(pre_save, sender=ProcessingStep, weak=False)
def processLog(sender, instance, **_kwargs):  # pylint: disable=unused-argument
    if instance.status != Status.ERROR:
        instance.log = ""


# noinspection PyUnusedLocal
@receiver(post_save, sender=ProcessingStep, weak=False)
def statusUpdate(sender, instance, **_kwargs):  # pylint: disable=unused-argument
    instance.process.updateStatus()
