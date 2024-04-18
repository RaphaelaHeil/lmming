from django.contrib.postgres.fields import ArrayField
from django.db.models import Model, PositiveIntegerField, SlugField, FileField, BooleanField, CharField, TextField, \
    ForeignKey, DateField, TextChoices, DateTimeField, CASCADE, OneToOneField
from django.utils import timezone

from utils import PipelineStepName


class Status(TextChoices):
    PENDING = "PENDING", "Pending"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETE = "COMPLETE", "Complete"
    ERROR = "ERROR", "Error"
    AWAITING_HUMAN_INPUT = "AWAITING_HUMAN_INPUT", "Awaiting Human Input"
    AWAITING_HUMAN_VALIDATION = "AWAITING_HUMAN_VALIDATION", "Awaiting Human Validation"


class Transfer(Model):
    name = CharField()
    dateCreated = DateField(auto_now_add=True)
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

    iiifArkSlug = SlugField()  # TODO: check settings
    atomArkSlug = SlugField()  # TODO: check settings

    transfer = ForeignKey(Transfer, on_delete=CASCADE)

    identifier = CharField()  # mandatory, URL, single value
    title = CharField()  # mandatory, plain text, single value
    creator = CharField()  # mandatory, plain text, single value
    date = DateField()  # mandatory, single or *multiple* years
    coverage = CharField(max_length=30, choices=UnionLevel.choices, default=UnionLevel.OTHER)  # mandatory, single value
    language = ArrayField(CharField())  # mandatory, multi-value
    spatial = ArrayField(CharField())  # mandatory, multi-value
    type = ArrayField(CharField(choices=DocumentType.choices))  # mandatory, multi-value
    license = ArrayField(CharField())  # mandatory, multi-value
    isVersionOf = CharField()  # mandatory, single value  (URL)
    isFormatOf = CharField(max_length=30, choices=DocumentFormat.choices)  # mandatory, multi-value
    relation = CharField()  # optional, URL, multi-value ?!
    created = DateField()  # optional, single year
    available = DateField(blank=True, null=True)  # optional, date
    accessRights = CharField(choices=AccessRights.choices,
                             default=AccessRights.NOT_RESTRICTED)  # optional/default = ???
    source = ArrayField(CharField(), blank=True)  # optional, multi-value, plain-text-name | url
    description = TextField()  # optional, single value


class Page(Model):
    report = ForeignKey(Report, on_delete=CASCADE)
    file = FileField()

    order = PositiveIntegerField(default=1)  # internal use, not for CSV

    identifier = CharField()  # URL TODO: this is built from the base IIIF URL ... do we really need a separate field for this?
    isPartOf = CharField()  # mandatory, URL, based on report.identifier ... can be built on demand ...
    transcriptionFile = FileField(blank=False)  # mandatory, file type can be plain text or ALTO xml
    transcription = TextField(blank=True)  # optional, single value
    normalisedTranscription = TextField(blank=True)  # optional, single value
    persons = ArrayField(CharField(), blank=True)  # optional
    organisations = ArrayField(CharField(), blank=True)  # optional
    locations = ArrayField(CharField(), blank=True)  # optional
    times = ArrayField(CharField(), blank=True)  # optional
    works = ArrayField(CharField(), blank=True)  # optional
    events = ArrayField(CharField(), blank=True)  # optional
    objects = ArrayField(CharField(), blank=True)  # optional
    measures = BooleanField(default=False)  # optional/default = False


class Job(Model):
    transfer = ForeignKey(Transfer, on_delete=CASCADE, related_name="jobs")
    report = OneToOneField(
        Report,
        on_delete=CASCADE,
        primary_key=True,
    )

    status = CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    dateCreated = DateField(auto_now_add=True)
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
    order = PositiveIntegerField()

    status = CharField(choices=Status.choices, default=Status.PENDING)
    log = TextField()
    humanValidation = BooleanField(default=False)
    mode = CharField(choices=ProcessingStepMode.choices, default=ProcessingStepMode.AUTOMATIC)
