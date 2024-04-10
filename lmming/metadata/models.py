from django.db import models
from django.db.models import Model, PositiveIntegerField, SlugField, FileField, BooleanField, CharField, TextField, \
    ForeignKey, DateField, TextChoices
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField


class Report(Model):
    class UnionLevel(models.TextChoices):
        # TODO: where do I add the standardised spellings for the csv?
        WORKPLACE = "workplace", "workplace"
        SECTION = "section", "section"
        DIVISION = "division", "division"
        DISTRICT = "district", "district"
        NATIONAL_BRANCH = "national branch", "national branch"
        NATIONAL_FEDERATION = "national federation", "national federation"
        INTERNATIONAL_BRANCH = "international branch", "international branch"
        INTERNATIONAL_FEDERATION = "international federation", "international federation"
        OTHER = "other", "other"

    class DocumentType(models.TextChoices):
        # TODO: where do I add the standardised spellings for the csv?
        ANNUAL_REPORT = "annual report", "annual report"
        FINANCIAL_STATEMENT = "financial statement", "financial statement"

    class DocumentFormat(TextChoices):
        PRINTED = "printed", "printed"
        HANDWRITTEN = "handwritten", "handwritten"
        TYPEWRITTEN = "typewritten", "typewritten"
        DIGITAL = "digital", "digital"

    iiifArkSlug = SlugField()  # TODO: check settings
    atomArkSlug = SlugField()  # TODO: check settings

    identifier = CharField()  # mandatory, URL, single value
    title = CharField() # mandatory, plain text, single value
    creator = CharField() # mandatory, plain text, single value
    relation = CharField() # optional, URL, multi-value ?!
    date = DateField()  # mandatory, single or multiple year TODO: check types of date fields # TODO: can be range of years ...
    created = DateField() # optional, single year
    coverage = models.CharField(max_length=30, choices=UnionLevel.choices, default=UnionLevel.OTHER) # mandatory, single value
    spatial = CharField() # mandatory, multi-value
    description = TextField() # optional, single value
    language = CharField() # mandatory, multi-value
    type = CharField(max_length=30, choices=DocumentType.choices)  # mandatory, multi-value
    isFormatOf = CharField(max_length=30, choices=DocumentFormat.choices)  # mandatory, multi-value
    license = ArrayField(CharField(), blank=True) # mandatory, multi-value
    available = DateField(blank=True, null=True) # optional
    accessRights = BooleanField(blank=True, null=True) # optional/default = ???
    source = ArrayField(CharField(), blank=True)  # optional, multi-value, plain-text-name | url
    isVersionOf = CharField()  # mandatory,, single value  (URL)


class Page(Model):
    order = PositiveIntegerField(default=1) # internal use, not for CSV

    report = ForeignKey(Report, on_delete=models.CASCADE)
    identifier = CharField()  # URL TODO: this is built from the base IIIF URL ... do we really need a separate field for this?
    isPartOf = CharField() # mandatory, URL, based on report.identifier ... can be built on demand ...
    transcriptionFile = FileField(blank=False) # mandatory, file type can be plain text or ALTO xml
    transcription = TextField(blank=True) # optional, single value
    normalisedTranscription = TextField(blank=True) # optional, single value
    persons = ArrayField(CharField(), blank=True) # optional
    organisations = ArrayField(CharField(), blank=True) # optional
    locations = ArrayField(CharField(), blank=True) # optional
    times = ArrayField(CharField(), blank=True) # optional
    works = ArrayField(CharField(), blank=True) # optional
    events = ArrayField(CharField(), blank=True) # optional
    objects = ArrayField(CharField(), blank=True) # optional
    measures = BooleanField(default=False)  # optional/default = False


class OldJob(Model):
    class JobStatus(models.TextChoices):
        PENDING = "PENDING", _("PENDING")
        IN_PROGRESS = "IN_PROGRESS", _("IN_PROGRESS")
        COMPLETE = "COMPLETE", _("COMPLETE")

    collectionName = models.CharField(max_length=40)
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.PENDING)
    metadata = models.FileField(blank=False)
    nerResult = models.FileField(blank=True)
    dateCreated = models.DateTimeField(auto_now_add=True)
    startDate = models.DateTimeField(null=True, blank=True)
    endDate = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.collectionName} - {self.status}"

    def started(self):
        self.startDate = timezone.now()
        self.status = self.JobStatus.IN_PROGRESS

    def completed(self):
        self.endDate = timezone.now()
        self.status = self.JobStatus.COMPLETE


class OldPage(models.Model):
    job = models.ForeignKey(OldJob, on_delete=models.CASCADE)
    file = models.FileField()
    originalFilename = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.originalFilename} ({self.job.pk})"


@receiver(pre_delete, sender=OldJob)
def jobFileDeleteHandler(sender, instance, **kwargs):
    instance.metadata.delete(save=False)
    instance.nerResult.delete(save=False)


@receiver(pre_delete, sender=OldPage)
def pageFileDeleteHandler(sender, instance, **kwargs):
    instance.file.delete(save=False)
