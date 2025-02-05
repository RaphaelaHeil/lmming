from django.contrib.postgres.fields import ArrayField
from django.db.models import Model, PositiveIntegerField, FileField, BooleanField, CharField, TextField, \
    ForeignKey, DateField, TextChoices, DateTimeField, CASCADE, OneToOneField, URLField, IntegerField, Q, Choices
from django.db.models.signals import pre_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


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
    lastUpdated = DateTimeField(auto_now=True, null=True)

    def updateTransferStatus(self):
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
    type = ArrayField(CharField(choices=DocumentType.choices), blank=True, null=True,
                      default=list, )  # mandatory, multi-value
    license = ArrayField(CharField(), blank=True, null=True)  # mandatory, multi-value
    isVersionOf = URLField(blank=True, null=True)  # mandatory, single value  (URL)
    isFormatOf = ArrayField(CharField(choices=DocumentFormat.choices), blank=True, null=True,
                            default=list, )  # mandatory, multi-value
    relation = ArrayField(CharField(), blank=True, null=True)  # optional, URL, multi-value ?!
    created = DateField(blank=True, null=True)  # optional, single year
    available = DateField(blank=True, null=True)  # optional, date
    accessRights = CharField(choices=AccessRights.choices, default=AccessRights.NOT_RESTRICTED, blank=True)  # optional
    source = ArrayField(CharField(), blank=True, null=True)  # optional, multi-value, plain-text-name | url
    description = TextField(blank=True, default="")  # optional, single value

    unionId = CharField(blank=True, default="")
    noid = CharField(blank=True, default="")

    references = CharField(blank=True, default="")
    referencesNoid = CharField(blank=True, default="")

    def dateString(self) -> str:
        if len(self.date) == 0:
            return ""
        elif len(self.date) == 1:
            return str(self.date[0].year)
        else:
            return ", ".join([str(d.year) for d in self.date])

    def get_type_display(self):
        return ", ".join([self.DocumentType[x].label for x in self.type] if self.type else [])

    def get_date_display(self):
        return ", ".join([str(x.year) for x in self.date])

    def get_language_display(self):
        return ", ".join(self.language if self.language else [])

    def get_spatial_display(self):
        return ", ".join(self.spatial)

    def get_license_display(self):
        return ", ".join(self.license if self.license else [])

    def get_isFormatOf_display(self):
        return ", ".join([self.DocumentFormat[x].label for x in self.isFormatOf] if self.isFormatOf else [])

    def get_source_display(self):
        return ", ".join(self.source if self.source else [])

    def get_accessRights_display(self):
        return self.AccessRights[self.accessRights].label

    def get_relation_display(self):
        return ", ".join(self.relation if self.relation else [])


class ReportTranslation(Model):
    report = ForeignKey(Report, on_delete=CASCADE)
    language = CharField(blank=True, default="")

    coverage = CharField(blank=True, default="")
    isFormatOf = ArrayField(CharField(), blank=True, null=True)
    type = ArrayField(CharField(), blank=True, null=True)
    accessRights = CharField(blank=True, default="")

    description = TextField(blank=True, default="")

    def get_isFormatOf_display(self):
        return ", ".join(self.isFormatOf if self.isFormatOf else [])

    def get_type_display(self):
        return ", ".join(self.type if self.type else [])


class Page(Model):
    report = ForeignKey(Report, on_delete=CASCADE)
    order = PositiveIntegerField(default=1)  # internal use, not for CSV
    transcriptionFile = FileField(blank=False, null=True)  # mandatory, file type can be plain text or ALTO xml
    originalFileName = CharField(blank=False, null=True)

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

    iiifId = CharField(blank=True, default="")  # iiif URL + structmap
    noid = CharField(blank=True, default="")
    source = CharField(blank=True, default="")
    bibCitation = CharField(blank=True, default="")


# noinspection PyUnusedLocal
@receiver(pre_delete, sender=Page, weak=False)
def pageFileDeleteHandler(sender, instance, **_kwargs):
    instance.transcriptionFile.delete(save=False)


class Job(Model):
    transfer = ForeignKey(ExtractionTransfer, on_delete=CASCADE, related_name="jobs")
    report = OneToOneField(Report, on_delete=CASCADE, primary_key=True)

    status = CharField(choices=Status.choices, default=Status.PENDING)
    dateCreated = DateTimeField(auto_now_add=True)
    startDate = DateTimeField(null=True, blank=True)
    endDate = DateTimeField(null=True, blank=True)
    lastUpdated = DateTimeField(auto_now=True, null=True)

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

    def getFirstStepNameAwaitingHumanInteraction(self):
        return self.processingSteps.order_by("order").filter(
            Q(status=Status.AWAITING_HUMAN_INPUT) | Q(
                status=Status.AWAITING_HUMAN_VALIDATION)).first().get_processingStepType_display()


# noinspection PyUnusedLocal
@receiver(post_save, sender=Job, weak=False)
def statusUpdateTransfer(sender, instance, **_kwargs):  # pylint: disable=unused-argument
    instance.transfer.updateTransferStatus()


class ProcessingStep(Model):
    class ProcessingStepType(Choices):
        FILENAME = "FILENAME", 10, "Filename-based extraction"
        FILEMAKER_LOOKUP = "FILEMAKER_LOOKUP", 20, "Lookup in Filemaker export"
        GENERATE = "GENERATE", 30, "Generate/Calculate"
        FAC_MANUAL = "FAC_MANUAL", 35, "Manual"
        IMAGE = "IMAGE", 40, "Image-based extraction"
        NER = "NER", 50, "Named Entity Recognition"
        MINT_ARKS = "MINT_ARKS", 60, "Mint ARKs"
        ARAB_GENERATE = "ARAB_GENERATE", 31, "Generate/Calculate"
        ARAB_MANUAL = "ARAB_MANUAL", 36, "Manual"
        ARAB_MINT_HANDLE = "ARAB_MINT_HANDLE", 61, "Mint Handle IDs"
        ARAB_TRANSLATE_TO_SWEDISH = "ARAB_TRANSLATE_TO_SWEDISH", 70, "Translate to Swedish"
        FAC_TRANSLATE_TO_SWEDISH = "FAC_TRANSLATE_TO_SWEDISH", 70, "Translate to Swedish"

        @property
        def order(self):
            return self._value_[1]

        @property
        def value(self):
            return self._value_[0]

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
        return (f"{self.job.pk} - {self.processingStepType} ({self.mode}"
                f"{', human validation' if self.humanValidation else ''})")


# noinspection PyUnusedLocal
@receiver(pre_save, sender=ProcessingStep, weak=False)
def processLog(sender, instance, **_kwargs):  # pylint: disable=unused-argument
    if instance.status != Status.ERROR:
        instance.log = ""


# noinspection PyUnusedLocal
@receiver(post_save, sender=ProcessingStep, weak=False)
def statusUpdate(sender, instance, **_kwargs):  # pylint: disable=unused-argument
    instance.job.updateStatus()


class DefaultValueSettings(Model):
    class Meta:
        verbose_name_plural = "default Value Settings"

    class DefaultValueSettingsType(TextChoices):
        DC_LANGUAGE = "DC_LANGUAGE", "dcterms:language"
        DC_LICENSE = "DC_LICENSE", "dcterms:license"
        DC_SOURCE = "DC_SOURCE", "dcterms:source"
        DC_ACCESS_RIGHTS = "DC_ACCESS_RIGHTS", "dcterms:accessRights"
        ARK_SHOULDER = "ARK_SHOULDER", "ARK Shoulder (deprecated)"
        REPORT_ARK_SHOULDER = "REPORT_ARK_SHOULDER", "Report-level ARK Shoulder"
        PAGE_ARK_SHOULDER = "PAGE_ARK_SHOULDER", "Page-level ARK Shoulder"

    name = CharField(primary_key=True, choices=DefaultValueSettingsType.choices)
    value = CharField(blank=True, default="")

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


class DefaultNumberSettings(Model):
    class Meta:
        verbose_name_plural = "default Number Settings"

    class DefaultNumberSettingsType(TextChoices):
        AVAILABLE_YEAR_OFFSET = "AVAILABLE_YEAR_OFFSET", ("Number of years, calculated from date of publication, until "
                                                          "the material becomes available")
        NER_NORMALISATION_END_YEAR = "NER_NORMALISATION_END_YEAR", ("Year after which the transcriptions should not be "
                                                                    "normalised anymore (given year is the final year"
                                                                    "that will be normalised)")

    name = CharField(primary_key=True, choices=DefaultNumberSettingsType.choices)
    value = IntegerField(blank=True, default=0)

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


class ExternalRecord(Model):
    archiveId = CharField(primary_key=True)
    organisationName = CharField()
    county = CharField(blank=True, default="")
    municipality = CharField(blank=True, default="")
    city = CharField(blank=True, default="")
    parish = CharField(blank=True, default="")
    relationLink = URLField(blank=True, default="")
    coverage = CharField(blank=True, default="")
    isVersionOfLink = URLField(blank=True, default="")


class InstituteSpecificData(Model):
    report = OneToOneField(Report, on_delete=CASCADE, primary_key=True, default=None)

    class Meta:
        abstract = True


class FacSpecificData(InstituteSpecificData):
    seriesVolumeName = CharField(blank=True, default="")
    seriesVolumeSignum = CharField(blank=True, default="")
