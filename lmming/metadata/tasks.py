import logging
from pathlib import Path

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.conf import settings

from metadata.enum_utils import PipelineStepName
from metadata.models import ProcessingStep, Job, Status, Report, FilemakerEntry, DefaultNumberSettings, \
    DefaultValueSettings
from metadata.nlp.ner import processPage
import requests
from requests.compat import urljoin

logger = logging.getLogger("lmming_celery")


@shared_task()
def extractFromFileNames(jobPk: int, pipeline: bool = True):
    # nothing to do at the moment ...
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILENAME).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    if pipeline:
        scheduleTask(jobPk)


@shared_task()
def fileMakerLookup(jobPk: int, pipeline: bool = True):
    report = Report.objects.get(job__pk=jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP).first()
    # fields: creator*[1], relation[n], coverage*[1], spatial*[N]

    entries = FilemakerEntry.objects.filter(archiveId=report.unionId)
    if entries.count() == 0:
        step.log = f"No Filemaker entry found for union with ID {report.unionId}."
        step.status = Status.ERROR
        step.save()
        return
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

    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()

    if pipeline:
        scheduleTask(jobPk)


@shared_task()
def computeFromExistingFields(jobPk: int, pipeline: bool = True):
    # fields: title*[1], created[1], description[1], available[1]
    report = Report.objects.get(job__pk=jobPk)

    # TODO: expand abbreviations in creator name!
    report.title = f"{report.creator} - {', '.join([Report.DocumentType[x].label for x in report.type])} ({report.dateString()})"
    created = sorted(report.date)[-1] + relativedelta(years=1)
    report.created = created

    pageCount = report.page_set.count()
    if pageCount != 1:
        report.description = f"{pageCount} pages"
    else:
        report.description = "1 page"
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

    if pipeline:
        scheduleTask(jobPk)


@shared_task()
def extractFromImage(jobPk: int, pipeline: bool = True):
    # fields: isFormatOf*[N]
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.IMAGE).first()
    step.status = Status.AWAITING_HUMAN_INPUT
    step.save()

    if pipeline:
        scheduleTask(jobPk)


@shared_task()
def namedEntityRecognition(jobPk: int, pipeline: bool = True):
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

    if pipeline:
        scheduleTask(jobPk)


@shared_task()
def mintArks(jobPk: int, pipeline: bool = True):
    report = Report.objects.get(job__pk=jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS).first()

    shoulder = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.ARK_SHOULDER).first()
    if not shoulder:
        shoulder = "/r1"
    arkletBaseUrl = settings.MINTER_URL
    headers = {"Authorization": f"Bearer {settings.MINTER_AUTH}"}
    mintBody = {"naan": settings.MINTER_ORG_ID, "shoulder": shoulder}

    mintUrl = urljoin(arkletBaseUrl, "mint")

    response = requests.post(mintUrl, headers=headers, json=mintBody)
    if response.ok:
        ark = response.json()["ark"]
        noid = ark.split("/")[-1]

        iiifBase = settings.IIIF_BASE_URL

        resolveTo = urljoin(iiifBase, f"iiif/presentation/{noid}/manifest")

        details = {"ark": ark,
                   "url": resolveTo,
                   "title": report.title,
                   # "metadata": metadata, # TODO: other things to add?
                   "type": report.get_type_display(),
                   # "commitment": commitment,
                   # "identifier": identifier,
                   "format": report.get_isFormatOf_display(),
                   "relation": report.get_relation_display(),
                   "source": report.get_source_display()}

        updateResponse = requests.put(url=urljoin(arkletBaseUrl, "update"), headers=headers, json=details)
        if updateResponse.ok:
            report.noid = noid
            report.identifier = ark
            report.save()
        else:
            step.log = (f"An error occurred while updating the ARK {ark}, status: {response.status_code}. Please verify"
                        f" that ARKlet is running and try again.")
            step.save()
            logger.warning(f"ARKlet returned status {updateResponse.status_code} while trying to update content for "
                           f"{ark} ({jobPk} - {report.title})")

    else:
        step.log = (f"An error occurred while obtaining a new ARK: {response.status_code}. Please verify that ARKlet is"
                    f" running and try again.")
        step.save()
        logger.warning(f"ARKlet returned status {response.status_code} while trying to mint ARK for {jobPk} - "
                       f"{report.title}")

    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()

    if pipeline:
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


def restartTask(jobId: int, stepType: ProcessingStep.ProcessingStepType):
    job = Job.objects.get(pk=jobId)
    step = job.processingSteps.filter(processingStepType=stepType).first()
    step.status = Status.IN_PROGRESS
    step.save()
    transaction.on_commit(lambda: TASK_INDEX[stepType].delay(jobId, False))


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
