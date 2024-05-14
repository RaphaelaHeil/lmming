from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction

from metadata.enum_utils import PipelineStepName
from metadata.models import ProcessingStep, Job, Status, Report, FilemakerEntry


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

    filemaker = FilemakerEntry.objects.filter(archiveId=report.unionId).first()

    report.creator = filemaker.organisationName
    report.relation = [""]  # TODO: not yet in FAC Filemaker CSV
    report.spatial = ["SE"] + [x for x in [filemaker.county, filemaker.municipality, filemaker.city, filemaker.parish]
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
    created = sorted(report.date)[-1] + relativedelta(year=1)
    report.created = created
    report.description = f"{report.page_set.count} pages"
    report.available = created + relativedelta(year=0)  # TODO: add years to settings DefaultNumberSettings.value
    report.save()

    print("computeFromExistingFields", jobPk)
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
    print("extractFromImage", jobPk)
    scheduleTask(jobPk)


@shared_task()
def namedEntityRecognition(jobPk: int):
    # fields: everything in page, except minting
    print("namedEntityRecognition", jobPk)
    report = Report.objects.get(job__pk=jobPk)
    for page in report.page_set.all():
        idx = page.order
        page.transcription = f"transcription {idx}"
        page.normalisedTranscription = f"normalised transcription {idx}"
        page.persons = [f"person 1 {idx}", f"person 2 {idx}"]
        page.organisations = [f"org 1 {idx}", f"org 2 {idx}"]
        page.locations = [f"loc 1 {idx}", f"loc 2 {idx}"]
        page.works = [f"works 1 {idx}", f"works 2 {idx}"]
        page.events = [f"events 1 {idx}", f" events 2{idx}"]
        page.ner_objects = [f"obj 1 {idx}", f"obj 2 {idx}"]
        page.measures = True
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

    report.identifier = "http://iiif.fauppsala.se"
    report.isVersionOf = "http://atom.fauppsala.se"
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
