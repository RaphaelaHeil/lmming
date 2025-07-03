import logging

from django.conf import settings
from django.db import transaction

from metadata.models import ProcessingStep, Job, Status
from metadata.tasks.arab import arabComputeFromExistingFields, arabMintHandle
from metadata.tasks.arab import translateToSwedish as arabTranslateToSwedish
from metadata.tasks.fac import computeFromExistingFields, extractFromImage, mintArks, translateToSwedish
from metadata.tasks.shared import extractFromFileNames, fileMakerLookup, namedEntityRecognition
from metadata.tasks.arab_other import arabOtherMintHandle, fileMakerLookupArabOther

logger = logging.getLogger(settings.WORKER_LOG_NAME)

TASK_INDEX = {ProcessingStep.ProcessingStepType.FILENAME.value: extractFromFileNames,
              ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.value: fileMakerLookup,
              ProcessingStep.ProcessingStepType.GENERATE.value: computeFromExistingFields,
              ProcessingStep.ProcessingStepType.IMAGE.value: extractFromImage,
              ProcessingStep.ProcessingStepType.NER.value: namedEntityRecognition,
              ProcessingStep.ProcessingStepType.MINT_ARKS.value: mintArks,
              ProcessingStep.ProcessingStepType.ARAB_GENERATE.value: arabComputeFromExistingFields,
              ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.value: arabMintHandle,
              ProcessingStep.ProcessingStepType.FAC_TRANSLATE_TO_SWEDISH.value: translateToSwedish,
              ProcessingStep.ProcessingStepType.ARAB_TRANSLATE_TO_SWEDISH.value: arabTranslateToSwedish,
              ProcessingStep.ProcessingStepType.ARAB_OTHER_MINT_HANDLE.value: arabOtherMintHandle,
              ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP_ARAB.value: fileMakerLookupArabOther,
              }


def restartTask(jobId: int, stepType: ProcessingStep.ProcessingStepType):
    step = ProcessingStep.objects.filter(processingStepType=stepType.value, job__pk=jobId).first()
    step.status = Status.IN_PROGRESS
    step.save()
    transaction.on_commit(lambda: TASK_INDEX[stepType.value].delay(jobId, False))


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
                transaction.on_commit(lambda: TASK_INDEX[step.processingStepType].delay(jobId))
                return True
        else:
            # either error or unknown state, don't do anything, just return
            # TODO: maybe add some logging?
            return False
