from django.contrib.postgres.fields import ArrayField
from django.db.models import Model, PositiveIntegerField, FileField, BooleanField, CharField, TextField, \
    ForeignKey, DateField, TextChoices, DateTimeField, CASCADE, OneToOneField, URLField
from django.utils import timezone

from .utils import PipelineStepName


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
        jobStatuses = set([job.status for job in self.jobs.all()])  # TODO: is this thread-safe?

        if Status.AWAITING_HUMAN_INPUT in jobStatuses:
            self.status = Status.AWAITING_HUMAN_INPUT
        elif Status.AWAITING_HUMAN_VALIDATION in jobStatuses:
            self.status = Status.AWAITING_HUMAN_VALIDATION
        elif len(jobStatuses) == 1:
            self.status = jobStatuses.pop()
        else:
            # mix of: pending, in progress, complete and error
            if Status.IN_PROGRESS in jobStatuses or Status.PENDING in jobStatuses:
                self.status = Status.IN_PROGRESS
            else:  # status is a mix of complete and error
                self.status = Status.ERROR


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

    identifier = URLField(blank=True)  # mandatory, URL, single value
    title = CharField(blank=True)  # mandatory, plain text, single value
    creator = CharField(blank=True)  # mandatory, plain text, single value
    date = ArrayField(DateField(), blank=True)  # mandatory, single or *multiple* years
    coverage = CharField(choices=UnionLevel.choices, default=UnionLevel.OTHER, blank=True)  # mandatory, single value
    language = ArrayField(CharField(), blank=True)  # mandatory, multi-value
    spatial = ArrayField(CharField(), blank=True)  # mandatory, multi-value
    type = ArrayField(CharField(choices=DocumentType.choices), blank=True)  # mandatory, multi-value
    license = ArrayField(CharField(), blank=True)  # mandatory, multi-value
    isVersionOf = URLField(blank=True)  # mandatory, single value  (URL)
    isFormatOf = CharField(choices=DocumentFormat.choices, blank=True)  # mandatory, multi-value
    relation = URLField(blank=True)  # optional, URL, multi-value ?!
    created = DateField(blank=True)  # optional, single year
    available = DateField(blank=True)  # optional, date
    accessRights = CharField(choices=AccessRights.choices, default=AccessRights.NOT_RESTRICTED, blank=True)  # optional
    source = ArrayField(CharField(), blank=True)  # optional, multi-value, plain-text-name | url
    description = TextField(blank=True)  # optional, single value


class Page(Model):
    report = ForeignKey(Report, on_delete=CASCADE)
    order = PositiveIntegerField(default=1)  # internal use, not for CSV
    transcriptionFile = FileField(blank=False)  # mandatory, file type can be plain text or ALTO xml

    identifier = URLField(blank=True)  # URL
    transcription = TextField(blank=True)  # optional, single value
    normalisedTranscription = TextField(blank=True)  # optional, single value
    persons = ArrayField(CharField(), blank=True)  # optional
    organisations = ArrayField(CharField(), blank=True)  # optional
    locations = ArrayField(CharField(), blank=True)  # optional
    times = ArrayField(CharField(), blank=True)  # optional
    works = ArrayField(CharField(), blank=True)  # optional
    events = ArrayField(CharField(), blank=True)  # optional
    ner_objects = ArrayField(CharField(), blank=True)  # optional
    measures = BooleanField(default=False)  # optional/default = False


class Job(Model):
    transfer = ForeignKey(ExtractionTransfer, on_delete=CASCADE, related_name="jobs")
    report = OneToOneField(
        Report,
        on_delete=CASCADE,
        primary_key=True,
    )

    status = CharField(choices=Status.choices, default=Status.PENDING)
    dateCreated = DateTimeField(auto_now_add=True)
    startDate = DateTimeField(null=True, blank=True)
    endDate = DateTimeField(null=True, blank=True)

    def updateStatus(self):
        stepStatuses = set([s.status for s in self.processingSteps.all()])  # TODO: is this thread-safe?
        if Status.ERROR in stepStatuses:
            self.status = Status.ERROR
        elif Status.AWAITING_HUMAN_INPUT in stepStatuses:
            self.status = Status.AWAITING_HUMAN_INPUT
        elif Status.AWAITING_HUMAN_VALIDATION in stepStatuses:
            self.status = Status.AWAITING_HUMAN_VALIDATION
        elif len(stepStatuses) == 1:
            self.status = stepStatuses.pop()
        else:
            self.status = Status.IN_PROGRESS

    def started(self):
        self.startDate = timezone.now()
        self.status = Status.IN_PROGRESS

    def completed(self):
        self.endDate = timezone.now()
        self.status = Status.COMPLETE


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
