import logging
from pathlib import Path

from celery import shared_task, signals
from django.conf import settings

from metadata.models import ProcessingStep, Status, ExternalRecord, Report
from metadata.nlp.hf_utils import download
from metadata.nlp.ner import processPage, NlpResult
from metadata.tasks.utils import resumePipeline, getFacCoverage, getArabCoverage

logger = logging.getLogger(settings.WORKER_LOG_NAME)


@shared_task()
def extractFromFileNames(jobPk: int, pipeline: bool = True):
    # nothing to do at the moment ...
    step = ProcessingStep.objects.filter(job_id=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILENAME.value).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()
    if pipeline:
        resumePipeline(jobPk)


@shared_task()
def fileMakerLookup(jobPk: int, pipeline: bool = True):
    report = Report.objects.get(job__pk=jobPk)
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.value
                                         ).first()
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

        if settings.ARCHIVE_INST == "FAC":
            report.coverage = getFacCoverage(filemaker.organisationName)
        else:
            report.coverage = getArabCoverage(filemaker.coverage)
        report.relation = [filemaker.catalogueLink if filemaker.catalogueLink else ""]
        report.spatial = ["SE"] + [x for x in
                                   [filemaker.county, filemaker.municipality, filemaker.city, filemaker.parish]
                                   if x]

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
                                         processingStepType=ProcessingStep.ProcessingStepType.NER.value).first()
    if step.humanValidation:
        step.status = Status.AWAITING_HUMAN_VALIDATION
        step.save()
    else:
        step.status = Status.COMPLETE
        step.save()

    if pipeline:
        resumePipeline(jobPk)


@signals.worker_ready.connect
def prepareNLP(**_kwargs):
    download()
    logger.info("Model download complete")
