from datetime import date

from celery import shared_task
from django.db import transaction

from metadata.enum_utils import PipelineStepName
from metadata.models import ProcessingStep, Job, Status, Report


@shared_task()
def extractFromFileNames(jobPk: int):
    # nothing to do at the moment ...
    print("extractFromFileNames", jobPk)

    step = ProcessingStep.objects.filter(job_id=jobPk, processingStepType=ProcessingStep.ProcessingStepType.FILENAME)[0]
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    scheduleTask(jobPk)


@shared_task()
def fileMakerLookup(jobPk: int):
    # use union ID to extract information from filemaker export
    report = Report.objects.get(job__pk=jobPk)

    # fields: creator*[1], relation[n], coverage*[1], spatial*[N]

    # TODO: constantly opening and closing the filemaker csv to look up one line seems overkill
    # can we keep the csv in memory?
    # or should we perhaps add it into the database, together with a last updated date?
    # DB lookup would be quite smooth, but how do we handle mass-updates from csv?
    report.creator = "creator"
    report.relation = ["rel1", "rel2"]
    report.coverage = Report.UnionLevel.DISTRICT
    report.spatial = ["spatial1", "spatial2"]
    report.save()

    print("fileMakerLookup", jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP)[0]
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

    report.title = "this is a title"
    report.created = date.today()
    report.description = "this is a description"
    report.available = date.today()
    report.save()

    print("computeFromExistingFields", jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.GENERATE)[0]
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
    step = ProcessingStep.objects.filter(job__pk=jobPk, processingStepType=ProcessingStep.ProcessingStepType.IMAGE)[0]
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
                                         processingStepType=ProcessingStep.ProcessingStepType.NER)[0]
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
                                         processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS)[0]
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
