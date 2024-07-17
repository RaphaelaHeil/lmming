import datetime
import json
import logging
from pathlib import Path
from typing import List

import requests
from celery import shared_task, signals
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db import transaction
from requests.compat import urljoin

from metadata.enum_utils import PipelineStepName
from metadata.models import ProcessingStep, Job, Status, Report, ExternalRecord, DefaultNumberSettings, \
    DefaultValueSettings
from metadata.nlp.hf_utils import download
from metadata.nlp.ner import processPage, NlpResult

logger = logging.getLogger(settings.WORKER_LOG_NAME)


# TODO: add error handling in case a transfer was deleted between scheduling and start of the respective step

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
    entries = ExternalRecord.objects.filter(archiveId=report.unionId)
    if entries.count() == 0:
        step.log = f"No Filemaker entry found for union with ID {report.unionId}."
        step.status = Status.ERROR
        step.save()
        return
    else:
        filemaker = entries.first()

        if not filemaker.organisationName:
            step.log = f"Organisation name is empty for union with ID {report.unionId}."
            step.status = Status.ERROR
            step.save()
            return

        report.creator = filemaker.organisationName
        report.relation = [filemaker.catalogueLink if filemaker.catalogueLink else ""]
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


def __splitIfNotNone__(value: str) -> List[str]:
    if value:
        return [x.strip() for x in value.split(",")]
    else:
        return []


@shared_task()
def computeFromExistingFields(jobPk: int, pipeline: bool = True):
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.GENERATE).first()
    # fields: title*[1], created[1], description[1], available[1]
    report = Report.objects.get(job__pk=jobPk)

    # TODO: expand abbreviations in creator name!
    report.title = f"{report.creator} - {', '.join([Report.DocumentType[x].label for x in report.type])} ({report.dateString()})"
    created = sorted(report.date)[-1] + relativedelta(years=1)
    report.created = created

    pageCount = report.page_set.count()
    if pageCount == 1:
        report.description = "1 page"
    else:
        report.description = f"{pageCount} pages"

    # available[1], language*[n], license*[n], accessRights*[1], source[n]
    language = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE).first()
    if language and language.value:
        report.language = __splitIfNotNone__(language.value)
    else:
        step.log = "No language was specified. Please update the system settings."
        step.status = Status.ERROR
        step.save()
        return

    license = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE).first()
    if license and license.value:
        report.license = __splitIfNotNone__(license.value)
    else:
        step.log = "No license was specified. Please update the system settings."
        step.status = Status.ERROR
        step.save()
        return

    yearOffset = DefaultNumberSettings.objects.filter(
        pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET).first()
    if yearOffset:
        if yearOffset.value < 0:
            step.log = "Specified year offset is negative. Please update the system settings."
            step.status = Status.ERROR
            step.save()
            return
        else:
            report.available = created + relativedelta(years=yearOffset.value)
    else:
        step.log = "No year offset was specified. Please update the system settings."
        step.status = Status.ERROR
        step.save()
        return

    if settings.ARCHIVE_INST == "FAC":
        if report.available > datetime.date.today():
            report.accessRights = Report.AccessRights.RESTRICTED
        else:
            report.accessRights = Report.AccessRights.NOT_RESTRICTED
    else:
        accessRights = DefaultValueSettings.objects.filter(
            pk=DefaultValueSettings.DefaultValueSettingsType.DC_ACCESS_RIGHTS).first()
        if accessRights and accessRights.value:
            report.accessRights = accessRights.value
        else:
            step.log = "No value was specified for 'accessRights'. Please update the system settings."
            step.status = Status.ERROR
            step.save()
            return

    source = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE).first()
    if source and source.value:
        report.source = __splitIfNotNone__(source.value)
    else:
        report.source = ""

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
        try:
            result = processPage(Path(page.transcriptionFile.path))
            if not result:
                result = NlpResult()
        except Exception as e:
            logger.error(f"{type(e).__name__} occurred during NER. {e.args}")
            result = NlpResult()

        page.transcription = result.text
        page.normalisedTranscription = result.normalised
        page.persons = list(result.persons)
        page.organisations = list(result.organisations)
        page.locations = list(result.locations)
        page.works = list(result.works)
        page.events = list(result.events)
        page.ner_objects = list(result.objects)
        page.times = list(result.times)
        page.measures = result.measures
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

    shoulderSetting = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.ARK_SHOULDER).first()
    if not shoulderSetting:
        step.status = Status.ERROR
        step.log = "The ARK Shoulder is not set. Please contact your admin to verify LMMing's configuration."
        step.save()
        logger.warning("ARK Shoulder is not set!")
        return

    shoulder: str = shoulderSetting.value
    if not shoulder:
        step.status = Status.ERROR
        step.log = "The ARK Shoulder is empty. Please contact your admin to verify LMMing's configuration."
        step.save()
        logger.warning("Empty ARK Shoulder!")
        return
    if not shoulder.startswith("/"):
        step.status = Status.ERROR
        step.log = (f"The ARK Shoulder should start with a slash but it is {shoulder}. Please contact your admin to "
                    f"verify LMMing's configuration.")
        step.save()
        logger.warning(f"ARK Shoulder does not start with a slash - {shoulder}")
        return
    arkletBaseUrl = settings.MINTER_URL
    headers = {"Authorization": f"Bearer {settings.MINTER_AUTH}"}

    mintUrl = urljoin(arkletBaseUrl, "mint")

    iiifBase = settings.IIIF_BASE_URL

    if not report.noid:
        mintBody = {"naan": settings.MINTER_ORG_ID, "shoulder": shoulder}
        response = requests.post(mintUrl, headers=headers, json=mintBody)

        if response.ok:
            ark = response.json()["ark"]
            noid = ark.split("/")[-1]
            report.noid = noid
            report.identifier = f"https://ark.fauppsala.se/{ark}/manifest"  # TODO: remove hardcoding once arklet is set up properly
            report.save()

            for page in report.page_set.all():
                page.iiifId = f"{report.noid}_{page.order}"
                page.identifier = urljoin(iiifBase, f"iiif/image/{page.iiifId}/info.json")
                page.save()
        else:
            step.status = Status.ERROR
            step.log = (f"An error occurred while obtaining a new ARK: {response.status_code}. Please verify that "
                        f"ARKlet is running and try again.")
            step.save()
            logger.warning(f"ARKlet returned status {response.status_code} while trying to mint ARK for {jobPk} - "
                           f"{report.title}")
            return

    ark = f"ark:/{settings.MINTER_ORG_ID}/{report.noid}"

    resolveTo = urljoin(iiifBase, f"iiif/presentation/{report.noid}")

    # only adding the bare minimum for now:
    details = {"ark": ark, "url": resolveTo, "title": report.title, }
    # OBS: if added, source has to be a *valid* URL, otherwise ARKlet will reject the request with a "Bad Request" response!

    updateResponse = requests.put(url=urljoin(arkletBaseUrl, "update"), headers=headers, json=details)
    if not updateResponse.ok:
        step.status = Status.ERROR
        step.log = (f"An error occurred while updating the ARK {ark}, status: {updateResponse.status_code}"
                    f". Please verify that ARKlet is running and try again.")
        step.save()
        logger.warning(f"ARKlet returned status {updateResponse.status_code} while trying to update content for "
                       f"{ark} ({jobPk} - {report.title})")
        return

    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()

    if pipeline:
        scheduleTask(jobPk)


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
                transaction.on_commit(lambda: TASK_INDEX[step.processingStepType].delay(jobId))
                return True
        else:
            # either error or unknown state, don't do anything, just return
            # TODO: maybe add some logging?
            return False


@signals.worker_ready.connect
def prepareNLP(**kwargs):
    download()
    logger.info("Model download complete")
