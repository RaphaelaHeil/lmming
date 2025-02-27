from typing import Dict, Any

from celery import shared_task

from v2.tasks.utils import updateStatus
from v2.models import Status


@shared_task()
def generateValues(processId: int, options: Dict[str, Any], continuePipeline: bool = True):
    stepKey = "generateValues"
    updateStatus(processId, stepKey, Status.IN_PROGRESS)

    updateStatus(processId, stepKey, Status.COMPLETE)
