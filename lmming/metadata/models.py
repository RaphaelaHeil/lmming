from django.contrib.postgres.fields import ArrayField
from django.db.models import Model, PositiveIntegerField, FileField, BooleanField, CharField, TextField, \
    ForeignKey, DateField, TextChoices, DateTimeField, CASCADE, OneToOneField, URLField
from django.db.models.signals import pre_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from metadata.enum_utils import PipelineStepName


class Status(TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETE = "COMPLETE", "Complete"
    ERROR = "ERROR", "Error"
    AWAITING_HUMAN_INPUT = "AWAITING_HUMAN_INPUT", "Awaiting Human Input"
    AWAITING_HUMAN_VALIDATION = "AWAITING_HUMAN_VALIDATION", "Awaiting Human Validation"


class ExtractionTransfer(Model):
    name = CharField()
    dateCreated = DateTimeField(auto_now_add=True)
    startDate = DateTimeField(null=True, blank=True)
    endDate = DateTimeField(null=True, blank=True)
    status = CharField(choices=Status.choices, default=Status.PENDING)

    def updateStatus(self):
        jobStatuses = set([job.status for job in self.jobs.all()])

        if self.status == Status.PENDING and len(jobStatuses) > 1:
            self.started()
        elif Status.AWAITING_HUMAN_INPUT in jobStatuses:
            self.status = Status.AWAITING_HUMAN_INPUT
        elif Status.AWAITING_HUMAN_VALIDATION in jobStatuses:
            self.status = Status.AWAITING_HUMAN_VALIDATION
        elif len(jobStatuses) == 1:
            status = jobStatuses.pop()
            if status == Status.COMPLETE:
                self.completed()
            else:
                self.status = status
        else:
            # mix of: pending, in progress, complete and error
            if Status.IN_PROGRESS in jobStatuses or Status.PENDING in jobStatuses:
                self.status = Status.IN_PROGRESS
            else:  # status is a mix of complete and error
                self.status = Status.ERROR
        self.save()

    def started(self):
        self.startDate = timezone.now()
        self.status = Status.IN_PROGRESS

    def completed(self):
        self.endDate = timezone.now()
        self.status = Status.COMPLETE


def spatialDefault():
    return list(["SE"])


class Report(Model):
    class UnionLevel(TextChoices):
        WORKPLACE = "WORKPLACE", "workplace"
        SECTION = "SECTION", "section"
        DIVISION = "DIVISION", "division"
        DISTRICT = "DISTRICT", "district"
        NATIONAL_BRANCH = "NATIONAL_BRANCH", "national branch"
        NATIONAL_FEDERATION = "NATIONAL_FEDERATION", "national federation"
        INTERNATIONAL_BRANCH = "INTERNATIONAL_BRANCH", "international branch"
        INTERNATIONAL_FEDERATION = "INTERNATIONAL_FEDERATION", "international federation"
        OTHER = "OTHER", "other"

    class DocumentType(TextChoices):
        ANNUAL_REPORT = "ANNUAL_REPORT", "annual report"
        FINANCIAL_STATEMENT = "FINANCIAL_STATEMENT", "financial statement"

    class DocumentFormat(TextChoices):
        PRINTED = "PRINTED", "printed"
        HANDWRITTEN = "HANDWRITTEN", "handwritten"
        TYPEWRITTEN = "TYPEWRITTEN", "typewritten"
        DIGITAL = "DIGITAL", "digital"

    class AccessRights(TextChoices):
        RESTRICTED = "RESTRICTED", "restricted"
        NOT_RESTRICTED = "NOT_RESTRICTED", "not restricted"

    transfer = ForeignKey(ExtractionTransfer, on_delete=CASCADE)

    identifier = URLField(blank=True, null=True)  # mandatory, URL, single value
    title = CharField(blank=True, default="")  # mandatory, plain text, single value
    creator = CharField(blank=True, default="")  # mandatory, plain text, single value
    date = ArrayField(DateField(), blank=True, null=True)  # mandatory, single or *multiple* years
    coverage = CharField(choices=UnionLevel.choices, default=UnionLevel.OTHER, blank=True)  # mandatory, single value
    language = ArrayField(CharField(), blank=True, null=True)  # mandatory, multi-value
    spatial = ArrayField(CharField(), blank=True, null=True, default=spatialDefault)  # mandatory, multi-value
    type = ArrayField(CharField(choices=DocumentType.choices), blank=True, null=True)  # mandatory, multi-value
    license = ArrayField(CharField(), blank=True, null=True)  # mandatory, multi-value
    isVersionOf = URLField(blank=True, null=True)  # mandatory, single value  (URL)
    isFormatOf = CharField(choices=DocumentFormat.choices, blank=True, null=True)  # mandatory, multi-value
    relation = ArrayField(CharField(), blank=True, null=True)  # optional, URL, multi-value ?!
    created = DateField(blank=True, null=True)  # optional, single year
    available = DateField(blank=True, null=True)  # optional, date
    accessRights = CharField(choices=AccessRights.choices, default=AccessRights.NOT_RESTRICTED, blank=True)  # optional
    source = ArrayField(CharField(), blank=True, null=True)  # optional, multi-value, plain-text-name | url
    description = TextField(blank=True, default="")  # optional, single value

    unionId = CharField(blank=True, default="")

    def dateString(self) -> str:
        if len(self.date) == 0:
            return ""
        elif len(self.date) == 1:
            return str(self.date[0].year)
        else:
            return ", ".join([str(d.year) for d in self.date])


class Page(Model):
    report = ForeignKey(Report, on_delete=CASCADE)
    order = PositiveIntegerField(default=1)  # internal use, not for CSV
    transcriptionFile = FileField(blank=False, null=True)  # mandatory, file type can be plain text or ALTO xml

    identifier = URLField(blank=True, null=True)  # URL
    transcription = TextField(blank=True, default="")  # optional, single value
    normalisedTranscription = TextField(blank=True, default="")  # optional, single value
    persons = ArrayField(CharField(), blank=True, null=True)  # optional
    organisations = ArrayField(CharField(), blank=True, null=True)  # optional
    locations = ArrayField(CharField(), blank=True, null=True)  # optional
    times = ArrayField(CharField(), blank=True, null=True)  # optional
    works = ArrayField(CharField(), blank=True, null=True)  # optional
    events = ArrayField(CharField(), blank=True, null=True)  # optional
    ner_objects = ArrayField(CharField(), blank=True, null=True)  # optional
    measures = BooleanField(default=False)  # optional/default = False


@receiver(pre_delete, sender=Page)
def pageFileDeleteHandler(sender, instance, **kwargs):
    instance.transcriptionFile.delete(save=False)


class Job(Model):
    transfer = ForeignKey(ExtractionTransfer, on_delete=CASCADE, related_name="jobs")
    report = OneToOneField(Report, on_delete=CASCADE, primary_key=True)

    status = CharField(choices=Status.choices, default=Status.PENDING)
    dateCreated = DateTimeField(auto_now_add=True)
    startDate = DateTimeField(null=True, blank=True)
    endDate = DateTimeField(null=True, blank=True)

    def updateStatus(self):
        stepStatuses = set([s.status for s in self.processingSteps.all()])
        if Status.ERROR in stepStatuses:
            self.status = Status.ERROR
        elif Status.AWAITING_HUMAN_INPUT in stepStatuses:
            self.status = Status.AWAITING_HUMAN_INPUT
        elif Status.AWAITING_HUMAN_VALIDATION in stepStatuses:
            self.status = Status.AWAITING_HUMAN_VALIDATION
        elif len(stepStatuses) == 1:
            status = stepStatuses.pop()
            if self.status != Status.COMPLETE and status == Status.COMPLETE:
                self.completed()
            else:
                self.status = status
        else:
            if self.status == Status.PENDING:
                self.started()
            else:
                self.status = Status.IN_PROGRESS
        self.save()

    def started(self):
        self.startDate = timezone.now()
        self.status = Status.IN_PROGRESS

    def completed(self):
        self.endDate = timezone.now()
        self.status = Status.COMPLETE


@receiver(post_save, sender=Job)
def statusUpdate(sender, instance, **kwargs):
    instance.transfer.updateStatus()


class ProcessingStep(Model):
    class ProcessingStepType(TextChoices):
        FILENAME = PipelineStepName.FILENAME.name, PipelineStepName.FILENAME.value[1]
        FILEMAKER_LOOKUP = PipelineStepName.FILEMAKER_LOOKUP.name, PipelineStepName.FILEMAKER_LOOKUP.value[1]
        GENERATE = PipelineStepName.GENERATE.name, PipelineStepName.GENERATE.value[1]
        IMAGE = PipelineStepName.IMAGE.name, PipelineStepName.IMAGE.value[1]
        NER = PipelineStepName.NER.name, PipelineStepName.NER.value[1]
        MINT_ARKS = PipelineStepName.MINT_ARKS.name, PipelineStepName.MINT_ARKS.value[1]

    class ProcessingStepMode(TextChoices):
        MANUAL = "MANUAL", "Manual"
        AUTOMATIC = "AUTOMATIC", "Automatic"

    job = ForeignKey(Job, on_delete=CASCADE, related_name="processingSteps")

    processingStepType = CharField(choices=ProcessingStepType.choices)
    order = PositiveIntegerField(default=1)

    status = CharField(choices=Status.choices, default=Status.PENDING)
    log = TextField(blank=True)
    humanValidation = BooleanField(default=False)
    mode = CharField(choices=ProcessingStepMode.choices, default=ProcessingStepMode.AUTOMATIC)

    def __str__(self):
        return f"{self.job.pk} - {self.processingStepType} ({self.mode}{', human validation' if self.humanValidation else ''})"


@receiver(post_save, sender=ProcessingStep)
def statusUpdate(sender, instance, **kwargs):
    instance.job.updateStatus()


class UrlSettings(Model):
    class Meta():
        verbose_name_plural = "url Settings"

    class UrlSettingsType(TextChoices):
        IIIF = "IIIF", "IIIF Base URL"
        ATOM = "ATOM", "AtoM Base URL"

    name = CharField(primary_key=True, choices=UrlSettingsType.choices)
    url = URLField()

    def __str__(self) -> str:
        return f"{self.name}: {self.url}"


class DefaultValueSettings(Model):
    class Meta():
        verbose_name_plural = "default Value Settings"

    class DefaultValueSettingsType(TextChoices):
        DC_LANGUAGE = "DC_LANGUAGE", "dcterms:language"
        DC_LICENSE = "DC_LICENSE", "dcterms:license"
        DC_SOURCE = "DC_SOURCE", "dcterms:source"

    name = CharField(primary_key=True, choices=DefaultValueSettingsType.choices)
    value = CharField(blank=True)

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"
