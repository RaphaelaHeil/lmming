from pathlib import Path

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction

from metadata.enum_utils import PipelineStepName
from metadata.models import ProcessingStep, Job, Status, Report, FilemakerEntry, DefaultNumberSettings, \
    DefaultValueSettings, UrlSettings
from metadata.nlp.ner import processPage


@shared_task()
def extractFromFileNames(jobPk: int):
    # nothing to do at the moment ...
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILENAME).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    scheduleTask(jobPk)


@shared_task()
def fileMakerLookup(jobPk: int):
    report = Report.objects.get(job__pk=jobPk)

    # fields: creator*[1], relation[n], coverage*[1], spatial*[N]

    entries = FilemakerEntry.objects.filter(archiveId=report.unionId)
    if entries.count() == 0:
        # log
        report.creator = "unknown"
        report.relation = [""]
        report.spatial = ["SE"]
        report.coverage = Report.UnionLevel.OTHER
    else:
        filemaker = entries.first()

        report.creator = filemaker.organisationName
        report.relation = [""]  # TODO: not yet in FAC Filemaker CSV
        report.spatial = ["SE"] + [x for x in
                                   [filemaker.county, filemaker.municipality, filemaker.city, filemaker.parish]
                                   if x]

        if "klubb" in filemaker.organisationName:
            report.coverage = Report.UnionLevel.WORKPLACE
        elif "sektion" in filemaker.organisationName:
            report.coverage = Report.UnionLevel.SECTION
        elif "avd" in filemaker.organisationName or "avdelning" in filemaker.organisationName:
            report.coverage = Report.UnionLevel.DIVISION
        elif "distrikt" in filemaker.organisationName:
            report.coverage = Report.UnionLevel.DISTRICT
        else:
            report.coverage = Report.UnionLevel.OTHER

    report.save()

    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    scheduleTask(jobPk)


@shared_task()
def computeFromExistingFields(jobPk: int):
    # fields: title*[1], created[1], description[1], available[1]
    report = Report.objects.get(job__pk=jobPk)

    # TODO: expand abbreviations in creator name!
    report.title = f"{report.creator} - {report.type} ({report.dateString()})"
    created = sorted(report.date)[-1] + relativedelta(years=1)
    report.created = created

    pageCount = report.page_set.count()
    if pageCount != 1:
        report.description = f"{pageCount} pages"
    else:
        report.description = f"1 page"
    report.available = created + relativedelta(
        years=DefaultNumberSettings.objects.filter(
            pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET).first().value)
    # TODO: language fix array vs comma separated string!
    report.language = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE).first().value.split(",")
    report.license = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE).first().value.split(",")
    report.accessRights = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.DC_ACCESS_RIGHTS).first().value
    report.source = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE).first().value.split("|")

    report.save()

    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.GENERATE).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    scheduleTask(jobPk)


@shared_task()
def extractFromImage(jobPk: int):
    # fields: isFormatOf*[N]
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.IMAGE).first()
    step.status = Status.AWAITING_HUMAN_INPUT
    step.save()
    scheduleTask(jobPk)


@shared_task()
def namedEntityRecognition(jobPk: int):
    # fields: everything in page, except minting
    report = Report.objects.get(job__pk=jobPk)
    for page in report.page_set.all():
        result = processPage(Path(page.transcriptionFile.path))
        page.transcription = result.text
        page.normalisedTranscription = result.normalised
        page.persons = list(result.persons)
        page.organisations = list(result.organisations)
        page.locations = list(result.locations)
        page.works = list(result.works)
        page.events = list(result.events)
        page.ner_objects = list(result.objects)
        page.times = list(result.times)
        page.measures = True
        page.save()
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.NER).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    scheduleTask(jobPk)


@shared_task()
def mintArks(jobPk: int):
    # field: identifier*[1], isVersionOf*[1]
    report = Report.objects.get(job__pk=jobPk)

    iiifArk = "ark1234"
    atomArk = "ark1234"

    report.identifier = UrlSettings.objects.filter(pk=UrlSettings.UrlSettingsType.IIIF).first().url + iiifArk
    report.isVersionOf = UrlSettings.objects.filter(pk=UrlSettings.UrlSettingsType.IIIF).first().url + atomArk
    report.save()

    print("mintARKs", jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    scheduleTask(jobPk)


def buildStructMap(transferId: int):
    pass


def buildFolderStructure(transferId: int):
    pass


TASK_INDEX = {PipelineStepName.FILENAME.name: extractFromFileNames,
              PipelineStepName.FILEMAKER_LOOKUP.name: fileMakerLookup,
              PipelineStepName.GENERATE.name: computeFromExistingFields,
              PipelineStepName.IMAGE.name: extractFromImage,
              PipelineStepName.NER.name: namedEntityRecognition,
              PipelineStepName.MINT_ARKS.name: mintArks}


def scheduleTask(jobId: int) -> bool:
    job = Job.objects.get(pk=jobId)
    for step in job.processingSteps.all().order_by("order"):
        if step.status in [Status.IN_PROGRESS, Status.AWAITING_HUMAN_VALIDATION, Status.AWAITING_HUMAN_INPUT]:
            # something is already running, resp. waiting, do not start anything else!
            # TODO: add logging
            return False
        if step.status == Status.COMPLETE:
            continue
        if step.status == Status.PENDING:
            if step.mode == ProcessingStep.ProcessingStepMode.MANUAL:
                step.status = Status.AWAITING_HUMAN_INPUT
                step.save()
                return False
            else:
                step.status = Status.IN_PROGRESS
                step.save()
                job.updateStatus()
                job.save()
                transaction.on_commit(lambda: TASK_INDEX[step.processingStepType].delay(jobId))
                return True
        else:
            # either error or unknown state, don't do anything, just return
            # TODO: maybe add some logging?
            return False
