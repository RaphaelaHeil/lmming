import logging

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings

from metadata.models import ProcessingStep, Status, Report, DefaultNumberSettings, DefaultValueSettings
from metadata.tasks.utils import resumePipeline
from metadata.tasks.utils import splitIfNotNone, createArabTitle

logger = logging.getLogger(settings.WORKER_LOG_NAME)


@shared_task()
def arabComputeFromExistingFields(jobPk: int, pipeline: bool = True):
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.ARAB_GENERATE.value
                                         ).first()

    # TODO language, title, license, isFormatOf, accessRights, created, available, source
    report = Report.objects.get(job__pk=jobPk)

    report.title = createArabTitle([Report.DocumentType[x] for x in report.type], report.date)
    report.created = sorted(report.date)[-1] + relativedelta(years=1)
    report.language = ["sv"]

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
    # TODO: impl
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    if pipeline:
        resumePipeline(jobPk)
