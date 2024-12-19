import datetime
import logging

import requests
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from requests.compat import urljoin

from metadata.i18n import SWEDISH
from metadata.models import ProcessingStep, Status, Report, DefaultNumberSettings, DefaultValueSettings, \
    ReportTranslation
from metadata.tasks.utils import resumePipeline, ArkletAdapter, ArkError
from metadata.tasks.utils import splitIfNotNone

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

    # shoulderSetting = DefaultValueSettings.objects.filter(
    #     pk=DefaultValueSettings.DefaultValueSettingsType.ARK_SHOULDER).first()

    reportShoulderSetting = ""
    pageShoulderSetting = ""

    if not reportShoulderSetting or not reportShoulderSetting.value:
        step.status = Status.ERROR
        step.log = "The ARK Shoulder for reports is not set. Please contact your admin to verify LMMing's configuration."
        step.save()
        logger.warning("ARK Shoulder for reports is not set or empty!")
        return

    if not pageShoulderSetting or not pageShoulderSetting.value:
        step.status = Status.ERROR
        step.log = "The ARK Shoulder for pages is not set. Please contact your admin to verify LMMing's configuration."
        step.save()
        logger.warning("ARK Shoulder for pages is not set is not set or empty!")
        return

    reportShoulder = reportShoulderSetting.value
    pageShoulder = pageShoulderSetting.value

    if not reportShoulder.startswith("/"):
        step.status = Status.ERROR
        step.log = (f"The ARK Shoulder for reports should start with a slash but it is {reportShoulder}. Please contact"
                    f" your admin to verify LMMing's configuration.")
        step.save()
        logger.warning(f"Report ARK shoulder does not start with a slash - {reportShoulder}")
        return

    if not pageShoulder.startswith("/"):
        step.status = Status.ERROR
        step.log = (f"The ARK Shoulder for pages should start with a slash but it is {pageShoulder}. Please contact "
                    f"your admin to verify LMMing's configuration.")
        step.save()
        logger.warning(f"Page ARK shoulder does not start with a slash - {pageShoulder}")
        return

    arkAdapter = ArkletAdapter(address=settings.MINTER_URL, naan=settings.MINTER_ORG_ID,
                               authenticationToken=settings.MINTER_AUTH)

    iiifBase = settings.IIIF_BASE_URL

    if report.noid:
        viewerArk = "http://ark.fauppsala.se/ark:/30441/r1wwjhb60rn"  # TODO: extract to settings
        resolveTo = viewerArk + "?manifest=" + iiifBase + f"iiif/presentation/{report.noid}/manifest"
        try:
            arkAdapter.updateArk(report.noid, {"url": resolveTo, "title": report.title})
            # OBS: if added, source has to be a *valid* URL, otherwise ARKlet will reject the request with a "Bad Request" response!
        except ArkError as e:
            step.status = Status.ERROR
            step.log = e.userMessage
            step.save()
            logger.warning(f"{report.title} (job: {jobPk}): {e.adminMessage}")
            return
    else:
        try:
            viewerArk = "http://ark.fauppsala.se/ark:/30441/r1wwjhb60rn"  # TODO: extract to settings
            resolveToFormat = viewerArk + "?manifest=" + iiifBase + "iiif/presentation/{}/manifest"

            ark = arkAdapter.createArkWithDependentUrl(reportShoulder, resolveToFormat, {"title": report.title})
            noid = ark.split("/")[-1]
            report.noid = noid
            report.identifier = f"https://ark.fauppsala.se/{ark}"  # TODO: remove hardcoding once arklet is set up properly
            report.save()
        except ArkError as e:
            step.status = Status.ERROR
            step.log = e.userMessage
            step.save()
            logger.warning(f"{report.title} (job: {jobPk}): {e.adminMessage}")
            return

    for page in report.page_set.all():
        if page.noid:
            resolveToFormat = iiifBase + "iiif/image/{}"
            ark = arkAdapter.updateArk(page.noid, {"url": resolveToFormat, "title": f"Page from '{report.title}'"})
            noid = ark.split("/")[-1]
            page.noid = noid
            arkLink = f"https://ark.fauppsala.se/{ark}"  # TODO: remove hardcoding once arklet is set up properly
            page.identifier = arkLink + "/info.json"
            page.source = arkLink + "/full/full/0/default.jpg"
            page.save()
        else:
            try:
                resolveToFormat = iiifBase + "iiif/image/{}"
                ark = arkAdapter.createArkWithDependentUrl(pageShoulder, resolveToFormat,
                                                           {"title": f"Page from '{report.title}'"})
                noid = ark.split("/")[-1]
                page.noid = noid
                arkLink = f"https://ark.fauppsala.se/{ark}"  # TODO: remove hardcoding once arklet is set up properly
                page.identifier = arkLink + "/info.json"
                page.source = arkLink + "/full/full/0/default.jpg"
                page.save()
            except ArkError as e:
                step.status = Status.ERROR
                step.log = e.userMessage
                step.save()
                logger.warning(f"{report.title} (job: {jobPk}): {e.adminMessage}")
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
    firstPage = report.page_set.first()

    filename = firstPage.originalFileName

    if "fac" in filename:
        filename = filename[filename.index("fac") + 4:]

    s = filename.split("_")
    typeName = s[1]

    if typeName.startswith("ars"):
        typeName = typeName.replace("ars", "års")

    if "berattelse" in typeName:
        typeName = typeName.replace("berattelse", "berättelse")

    if pageCount == 1:
        translation.description = "1 sida; " + typeName
    else:
        translation.description = f"{pageCount} sidor; " + typeName

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
