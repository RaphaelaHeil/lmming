from typing import List

from v2.models import ProcessingStep, Status


def resumePipeline(jobPk):
    from v2.tasks.manage import scheduleTask
    scheduleTask(jobPk)


def splitIfNotNone(value: str) -> List[str]:
    if value:
        return [x.strip() for x in value.split(",")]
    else:
        return []


def updateStatus(processId: int, stepKey: str, newStatus: Status):
    step = ProcessingStep.objects.filter(configuration__key=stepKey, process__pk=processId).first()
    step.status = newStatus
    step.save()


def updateError(processId: int, stepKey: str, errorMessage: str):
    step = ProcessingStep.objects.filter(configuration__key=stepKey, process__pk=processId).first()
    step.status = Status.ERROR
    step.log = errorMessage
    step.save()
