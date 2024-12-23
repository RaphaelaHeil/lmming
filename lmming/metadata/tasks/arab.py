import datetime
import logging
import secrets
from urllib.parse import urljoin

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings

from metadata.i18n import SWEDISH
from metadata.models import ProcessingStep, Status, Report, DefaultNumberSettings, DefaultValueSettings, \
    ReportTranslation
from metadata.tasks.utils import resumePipeline, HandleAdapter, HandleError
from metadata.tasks.utils import splitIfNotNone, createArabTitle

logger = logging.getLogger(settings.WORKER_LOG_NAME)

BETANUMERIC = "0123456789bcdfghjkmnpqrstvwxz"
BETA = "bcdfghjkmnpqrstvwxz"


@shared_task()
def arabComputeFromExistingFields(jobPk: int, pipeline: bool = True):
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.ARAB_GENERATE.value
                                         ).first()

    report = Report.objects.get(job__pk=jobPk)

    report.created = sorted(report.date)[-1] + relativedelta(years=1)
    report.language = ["sv"]

    translation = ReportTranslation.objects.filter(report=report, language="sv")
    if not translation:
        translation = ReportTranslation(report=report, language="sv")
    else:
        translation = translation.first()

    pageCount = report.page_set.count()
    if pageCount == 1:
        report.description = "1 page"
        translation.description = "1 sida"
    else:
        report.description = f"{pageCount} pages"
        translation.description = f"{pageCount} sidor"
    translation.save()

    report.isFormatOf = [Report.DocumentFormat.PRINTED]

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
def arabMintHandle(jobPk: int, pipeline: bool = True):
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.value
                                         ).first()
    report = Report.objects.get(job__pk=jobPk)

    iiifBase = settings.IIIF_BASE_URL
    handleServerIp = settings.ARAB_HANDLE_ADDRESS
    handleServerPort = settings.ARAB_HANDLE_PORT
    privateKeyFile = settings.ARAB_PRIVATE_KEY_FILE
    handleAdmin = settings.ARAB_HANDLE_ADMIN
    prefix = settings.ARAB_HANDLE_PREFIX
    certFile = settings.ARAB_CERT_FILE

    handleAdapter = HandleAdapter(address=handleServerIp, port=handleServerPort, prefix=prefix, user=handleAdmin,
                                  userKeyFile=privateKeyFile, certificateFile=certFile)

    if not report.noid:
        retries = 0
        while retries < settings.ARAB_RETRIES:
            try:
                # OBS: xml:IDs may not start with a digit!
                noid = "".join([secrets.choice(BETA)] + [secrets.choice(BETANUMERIC) for _ in range(14)])
                if handleAdapter.doesHandleAlreadyExist(noid):
                    retries += 1
                    continue

                resolveTo = urljoin(iiifBase, f"iiif/presentation/{noid}")
                handle = handleAdapter.createHandle(noid, resolveTo)

                if handle:
                    report.noid = noid
                    report.identifier = f"https://hdl.handle.net/{handle}?urlappend=/manifest"
                    report.save()
                    for page in report.page_set.all():
                        page.iiifId = f"{report.noid}_{page.order}"
                        page.identifier = urljoin(iiifBase, f"iiif/image/{page.iiifId}/info.json")
                        page.save()
                    if step.humanValidation:
                        step.status = Status.AWAITING_HUMAN_VALIDATION
                        step.save()
                    else:
                        step.status = Status.COMPLETE
                        step.save()
                    if pipeline:
                        resumePipeline(jobPk)
                    return
            except HandleError as handleError:
                step.log = handleError.userMessage
                logger.warning(handleError.adminMessage)
                step.status = Status.ERROR
                step.save()
                return
            except Exception as e:
                step.log = "An exception occurred. Please try again or contact your administrator if the issue persists."
                logger.warning(f"{e.args}")
                step.status = Status.ERROR
                step.save()
                return

        step.log = f"Could not generate unique handle. Made {retries} attempt(s)."
        step.status = Status.ERROR
        step.save()
    else:
        if step.humanValidation:
            step.status = Status.AWAITING_HUMAN_VALIDATION
            step.save()
        else:
            step.status = Status.COMPLETE
            step.save()
        if pipeline:
            resumePipeline(jobPk)
        return


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

    translation.save()

    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.ARAB_TRANSLATE_TO_SWEDISH.value).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()

    if pipeline:
        resumePipeline(jobPk)
