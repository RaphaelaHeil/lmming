import logging
from urllib.parse import urljoin

import pyhandle
from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.conf import settings
from pyhandle.handleexceptions import HandleAlreadyExistsException, HandleAuthenticationError, HandleSyntaxError

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
    report = Report.objects.get(job__pk=jobPk)

    iiifBase = settings.IIIF_BASE_URL
    handleServerUrl = settings.ARAB_HANDLE_URL
    handleOwner = settings.ARAB_HANDLE_OWNER
    privateKeyFile = settings.ARAB_PRIVATE_KEY_FILE
    certificateFile = settings.ARAB_CERTIFICATE_FILE
    prefix = settings.ARAB_HANDLE_PREFIX

    try:
        creds = pyhandle.clientcredentials.PIDClientCredentials(client="rest", handle_server_url=handleServerUrl,
                                                                handleowner=handleOwner, prefix=prefix,
                                                                private_key=privateKeyFile,
                                                                certificate_only=certificateFile)

        client = pyhandle.handleclient.RESTHandleClient.instantiate_with_credentials(creds)
    except Exception as e:
        step.log = "An exception occurred. Please try again or contact your administrator if the issue persists."
        logger.warning(f"{e.args}")
        step.status = Status.ERROR
        step.save()
        return

    retries = 0
    while retries < settings.ARAB_RETRIES:
        try:
            handle = client.generate_PID_name(prefix)  # TODO: this or a different format?
            noid = handle.split("/")[-1]
            resolveTo = urljoin(iiifBase, f"iiif/presentation/{noid}")
            extrainfo = {"URL": resolveTo}
            if report.title:
                extrainfo["DESC"] = report.title
            handleName = client.register_handle_kv(handle, overwrite=False, kv=extrainfo)

            report.noid = noid
            report.identifier = urljoin("https://hdl.handle.net", handleName)
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
        except HandleAlreadyExistsException as e:
            retries += 1
        except HandleAuthenticationError as e:
            step.log = "Could not authenticate with handle server. Please contact your administrator."
            logger.warning(f"HandleAuthenticationError {e.msg}")
            step.status = Status.ERROR
            step.save()
            return
        except HandleSyntaxError as e:
            step.log = "Handle does not have the expected syntax. Please contact your administrator."
            logger.warning(f"HandleSyntaxError {e.msg}")
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
