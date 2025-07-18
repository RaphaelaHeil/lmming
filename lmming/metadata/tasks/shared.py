import logging
from pathlib import Path

from celery import shared_task, signals
from django.conf import settings

from metadata.models import ProcessingStep, Status, ExternalRecord, Report, DefaultNumberSettings
from metadata.nlp.hf_utils import download
from metadata.nlp.ner import processPage, NlpResult
from metadata.tasks.utils import resumePipeline, getFacCoverage

logger = logging.getLogger(settings.WORKER_LOG_NAME)


def __dateCheck(report, externalRecords):
    candidates = set()
    for d in report.date:
        for entry in externalRecords:
            if not entry.startDate and not entry.endDate:
                candidates.add(entry)
            if entry.startDate:
                if d >= entry.startDate:
                    if entry.endDate and d > entry.endDate:
                        continue
                    else:
                        candidates.add(entry)
            else:
                if entry.endDate and d <= entry.endDate:
                    candidates.add(entry)
    return candidates


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
                message = f"No Organisation with matching date range found in external record for union with ID {report.unionId} and date {report.get_date_display()}."
            else:
                message = f"Found several matching dates in external record for union ID {report.unionId} and date {report.get_date_display()}."
            step.log = message
            step.status = Status.ERROR
            step.save()
            return

    if not filemaker.organisationName:
        step.log = f"No Organisation name given in external record for union with ID {report.unionId}."
        step.status = Status.ERROR
        step.save()
        return

    report.creator = filemaker.organisationName
    report.relation = [filemaker.relationLink if filemaker.relationLink else ""]
    report.spatial = ["SE"] + [x for x in
                               [filemaker.county, filemaker.municipality, filemaker.city, filemaker.parish]
                               if x]

    if settings.ARCHIVE_INST == "FAC":
        report.coverage = getFacCoverage(filemaker.organisationName)
        report.isVersionOf = filemaker.isVersionOfLink if filemaker.isVersionOfLink else "https://forskarsal.e-arkivportalen.se/"
    else:
        report.coverage = Report.UnionLevel.NATIONAL_BRANCH
        report.isVersionOf = filemaker.isVersionOfLink if filemaker.isVersionOfLink else f"https://www.arbark.se/ Arbetarrörelsens arkiv och bibliotek - SE/ARAB/{report.unionId}"

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
    step = ProcessingStep.objects.filter(job__pk=jobPk,
                                         processingStepType=ProcessingStep.ProcessingStepType.NER.value).first()

    normalisationCutOff = DefaultNumberSettings.objects.filter(
        pk=DefaultNumberSettings.DefaultNumberSettingsType.NER_NORMALISATION_END_YEAR).first()
    if normalisationCutOff:
        if report.created and (report.created.year <= normalisationCutOff.value):
            normalise = True
        else:
            normalise = False
    else:
        step.log = "No normalisation cut-off year was specified. Please update the system settings."
        step.status = Status.ERROR
        step.save()
        return

    for page in report.page_set.all():
        try:
            result = processPage(Path(page.transcriptionFile.path), normalise)
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
