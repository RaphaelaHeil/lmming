from typing import Dict, Any
from celery import shared_task


@shared_task()
def createIIIFHandles(processId: int, options: Dict[str, Any], continuePipeline: bool = True):
    stepKey = "createIIIFHandles"


#
# def createPlainHandles(processId: int, options: Dict[str, Any], continuePipeline: bool = True):
#     stepKey = "createPlainHandles"
#     updateStatus(processId, stepKey, Status.IN_PROGRESS)
#
#     if "fields" not in options:
#         # TODO: logger
#         updateStatus(processId, stepKey, Status.COMPLETE)
#
#     fields = options["fields"] # (level, fieldname)
#     for level, fieldName in fields:
#         assignments = MetadataAssignment.objects.find(projectMetadataTerm__metadataTerm__standardTerm=fieldName)
#         for a in assignments:
#             handleField = a.value
#             resolveTo = a.value.resolveTo
#             a.value.handle = None # TODO
#             a.save()
#
#     updateStatus(processId, stepKey, Status.COMPLETE)
#
