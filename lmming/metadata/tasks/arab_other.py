import logging
import secrets

from celery import shared_task
from django.conf import settings

from metadata.models import ProcessingStep, Status, ExternalRecord, Report
from metadata.tasks.arab import BETA, BETANUMERIC
from metadata.tasks.shared import __dateCheck
from metadata.tasks.utils import resumePipeline, HandleAdapter, HandleError, HandleLocation
from metadata.utils import formatDateString

logger = logging.getLogger(settings.WORKER_LOG_NAME)


@shared_task()
def fileMakerLookupArabOther(jobPk: int, pipeline: bool = True):
    report = Report.objects.get(job__pk=jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP_ARAB.value
                                         ).first()
    entries = ExternalRecord.objects.filter(arabRecordId=report.unionId)
    if entries.count() == 0:
        step.log = f"No entry found in external record for union with ID {report.unionId}."
        step.status = Status.ERROR
        step.save()
        return
    else:
        candidates = __dateCheck(report, entries)
        if len(candidates) == 1:
            filemaker = candidates.pop()
        else:
            if len(candidates) == 0:
                message = f"No creator with matching date range found in external record for creator with ID {report.unionId} and date {report.get_date_display()}."
            else:
                message = f"Found several matching dates in external record for creator ID {report.unionId} and date {report.get_date_display()}."
            step.log = message
            step.status = Status.ERROR
            step.save()
            return

    if not filemaker.organisationName:
        step.log = f"No creator name given in external record for record with ID {report.unionId}."
        step.status = Status.ERROR
        step.save()
        return

    report.creator = filemaker.organisationName

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
def arabOtherMintHandle(jobPk: int, pipeline: bool = True):
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.ARAB_OTHER_MINT_HANDLE.value
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

    viewerHandle = "http://hdl.handle.net/20.500.14494/tn84kt4mmznbqc2"  # TODO: extract to settings

    if report.noid:
        manifestLink = iiifBase + f"iiif/presentation/{report.noid}/manifest"
        try:
            handle = handleAdapter.updatePlainHandle(report.noid, manifestLink)
            report.identifier = f"https://hdl.handle.net/{handle}"
            report.save()
        except HandleError as handleError:
            step.log = handleError.userMessage
            logger.warning(handleError.adminMessage)
            step.status = Status.ERROR
            step.save()
            return
    else:
        retries = 0
        while retries < settings.ARAB_RETRIES:
            try:
                # OBS: xml:IDs may not start with a digit!
                noid = "".join([secrets.choice(BETA)] + [secrets.choice(BETANUMERIC) for _ in range(14)])
                if handleAdapter.doesHandleAlreadyExist(noid):
                    retries += 1
                    continue

                handle = handleAdapter.createPlainHandle(noid, iiifBase + f"iiif/presentation/{noid}/manifest")

                if handle:
                    report.noid = noid
                    report.identifier = f"https://hdl.handle.net/{handle}"
                    report.save()
                    break
            except HandleError as handleError:
                step.log = handleError.userMessage
                logger.warning(handleError.adminMessage)
                step.status = Status.ERROR
                step.save()
                return
        else:
            step.log = f"Could not generate unique handle. Made {retries} attempt(s)."
            step.status = Status.ERROR
            step.save()

    viewerLink = viewerHandle + "?urlappend=?manifest=" + iiifBase + f"iiif/presentation/{report.noid}/manifest"

    if report.referencesNoid:
        try:
            handle = handleAdapter.updatePlainHandle(report.referencesNoid, viewerLink)
            report.references = f"https://hdl.handle.net/{handle}"
            report.save()
        except HandleError as handleError:
            step.log = handleError.userMessage
            logger.warning(handleError.adminMessage)
            step.status = Status.ERROR
            step.save()
            return
    else:
        retries = 0
        while retries < settings.ARAB_RETRIES:
            try:
                # OBS: xml:IDs may not start with a digit!
                referencesNoid = "".join([secrets.choice(BETA)] + [secrets.choice(BETANUMERIC) for _ in range(14)])
                if handleAdapter.doesHandleAlreadyExist(referencesNoid):
                    retries += 1
                    continue

                handle = handleAdapter.createPlainHandle(referencesNoid, viewerLink)

                if handle:
                    report.referencesNoid = referencesNoid
                    report.references = f"https://hdl.handle.net/{handle}"
                    report.save()
                    break
            except HandleError as handleError:
                step.log = handleError.userMessage
                logger.warning(handleError.adminMessage)
                step.status = Status.ERROR
                step.save()
                return
        else:
            step.log = f"Could not generate unique handle. Made {retries} attempt(s)."
            step.status = Status.ERROR
            step.save()

    bibCitationBase = f"{report.title} ({formatDateString(report.date, ',')}) "

    for page in report.page_set.all():
        if page.noid:
            resolveToBase = iiifBase + f"iiif/image/{page.noid}"

            locations = [HandleLocation(1, resolveToBase + "/info.json"),
                         HandleLocation(0, resolveToBase + "/full/full/0/default.jpg", "jpgfull"),
                         HandleLocation(0, resolveToBase + "/info.json", "manifest")]

            try:
                handle = handleAdapter.updateLocationBasedHandle(page.noid, locations)

                page.iiifId = page.noid
                page.identifier = f"https://hdl.handle.net/{handle}?locatt=view:manifest"
                page.source = f"https://hdl.handle.net/{handle}?locatt=view:jpgfull"
                page.bibCitation = bibCitationBase + page.source
                page.save()
            except HandleError as handleError:
                step.log = handleError.userMessage
                logger.warning(handleError.adminMessage)
                step.status = Status.ERROR
                step.save()
                return
        else:
            retries = 0
            while retries < settings.ARAB_RETRIES:
                try:
                    # OBS: xml:IDs may not start with a digit!
                    noid = "".join([secrets.choice(BETA)] + [secrets.choice(BETANUMERIC) for _ in range(14)])
                    if handleAdapter.doesHandleAlreadyExist(noid):
                        retries += 1
                        continue

                    page.noid = noid

                    resolveToBase = iiifBase + f"iiif/image/{page.noid}"

                    locations = [HandleLocation(1, resolveToBase + "/info.json"),
                                 HandleLocation(0, resolveToBase + "/full/full/0/default.jpg", "jpgfull"),
                                 HandleLocation(0, resolveToBase + "/info.json", "manifest")]

                    handle = handleAdapter.updateLocationBasedHandle(page.noid, locations)
                    page.iiifId = page.noid
                    page.identifier = f"https://hdl.handle.net/{handle}?locatt=view:manifest"
                    page.source = f"https://hdl.handle.net/{handle}?locatt=view:jpgfull"

                    page.bibCitation = bibCitationBase + page.source
                    page.save()
                    break
                except HandleError as handleError:
                    step.log = handleError.userMessage
                    logger.warning(handleError.adminMessage)
                    step.status = Status.ERROR
                    step.save()
                    return
            else:
                step.log = f"Could not generate unique handle. Made {retries} attempt(s)."
                step.status = Status.ERROR
                step.save()

    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    if pipeline:
        resumePipeline(jobPk)
    return
