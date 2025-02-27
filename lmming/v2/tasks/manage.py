import logging

from django.conf import settings
from django.db import transaction

from v2.models import Process, Status, ProcessingStepMode
from v2.tasks.index import STEP_INDEX

logger = logging.getLogger(settings.WORKER_LOG_NAME)


# def restartTask(processId: int, stepKey: str):
#     updateStatus(processId, stepKey, Status.QUEUED)
#     transaction.on_commit(lambda: STEP_INDEX[stepKey].delay(processId, step.configuration.options, False))


def scheduleTask(processId: int) -> bool:
    process = Process.objects.get(pk=processId)
    for step in process.processingSteps.all().order_by("configuration__order"):
        if step.status in [Status.IN_PROGRESS, Status.QUEUED, Status.AWAITING_HUMAN_VALIDATION,
                           Status.AWAITING_HUMAN_INPUT]:
            # something is already running, resp. waiting, do not start anything else!
            # TODO: add logging
            return False
        if step.status == Status.COMPLETE:
            continue
        if step.status == Status.PENDING:
            if step.mode == ProcessingStepMode.MANUAL:
                step.status = Status.AWAITING_HUMAN_INPUT
                step.save()
                return False
            else:
                step.status = Status.QUEUED
                step.save()
                transaction.on_commit(
                    lambda: STEP_INDEX[step.configuration.key].delay(processId, step.configuration.options))
                return True
        else:
            # either error or unknown state, don't do anything, just return
            # TODO: maybe add some logging?
            return False
