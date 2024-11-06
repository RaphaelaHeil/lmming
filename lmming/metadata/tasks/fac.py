import datetime
import logging

import requests
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from requests.compat import urljoin

from metadata.models import ProcessingStep, Status, Report, DefaultNumberSettings, DefaultValueSettings, \
    ReportTranslation
from metadata.tasks.utils import resumePipeline
from metadata.tasks.utils import splitIfNotNone
from metadata.i18n import SWEDISH

logger = logging.getLogger(settings.WORKER_LOG_NAME)


@shared_task()
def computeFromExistingFields(jobPk: int, pipeline: bool = True):
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value).first()
    # fields: title*[1], created[1], description[1], available[1]
    report = Report.objects.get(job__pk=jobPk)

    # TODO: expand abbreviations in creator name!
    report.title = (f"{report.creator} - {', '.join([Report.DocumentType[x].label for x in report.type])} "
                    f"({report.dateString()})")
    report.created = sorted(report.date)[-1] + relativedelta(years=1)

    pageCount = report.page_set.count()
    if pageCount == 1:
        report.description = "1 page"
    else:
        report.description = f"{pageCount} pages"

    # available[1], language*[n], license*[n], accessRights*[1], source[n]
    language = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE).first()
    if language and language.value:
        report.language = splitIfNotNone(language.value)
    else:
        step.log = "No language was specified. Please update the system settings."
        step.status = Status.ERROR
        step.save()
        return

    license = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE).first()
    if license and license.value:
        report.license = splitIfNotNone(license.value)
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
            report.available = report.created + relativedelta(years=yearOffset.value)
    else:
        step.log = "No year offset was specified. Please update the system settings."
        step.status = Status.ERROR
        step.save()
        return

    if report.available > datetime.date.today():
        report.accessRights = Report.AccessRights.RESTRICTED
    else:
        report.accessRights = Report.AccessRights.NOT_RESTRICTED

    source = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE).first()
    if source and source.value:
        report.source = splitIfNotNone(source.value)
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
        resumePipeline(jobPk)


@shared_task()
def extractFromImage(jobPk: int, pipeline: bool = True):
    # fields: isFormatOf*[N]
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.IMAGE.value).first()
    step.status = Status.AWAITING_HUMAN_INPUT
    step.save()

    if pipeline:
        resumePipeline(jobPk)


@shared_task()
def mintArks(jobPk: int, pipeline: bool = True):
    report = Report.objects.get(job__pk=jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value).first()

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
        resumePipeline(jobPk)


@shared_task()
def translateToSwedish(jobPk: int, pipeline: bool = True):
    report = Report.objects.get(job__pk=jobPk)

    translation = ReportTranslation.objects.filter(report=report, language="sv")
    if not translation:
        translation = ReportTranslation(report=report, language="sv")
    else:
        translation = translation.first()

    translation.coverage = SWEDISH.coverage[Report.UnionLevel[report.coverage].label]
    translation.type = [SWEDISH.type[Report.DocumentType[x].label] for x in report.type]
    translation.isFormatOf = [SWEDISH.isFormatOf[Report.DocumentFormat[x].label] for x in report.isFormatOf]
    translation.accessRights = SWEDISH.accessRights[Report.AccessRights[report.accessRights].label]
    pageCount = report.page_set.count()
    if pageCount == 1:
        translation.description = "1 sida; " + ",".join(translation.type)
    else:
        translation.description = f"{pageCount} sidor; " + ",".join(translation.type)

    translation.save()

    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FAC_TRANSLATE_TO_SWEDISH.value).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()

    if pipeline:
        resumePipeline(jobPk)
