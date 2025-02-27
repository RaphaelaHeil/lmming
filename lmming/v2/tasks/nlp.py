from pathlib import Path
from typing import Dict, Any

from celery import shared_task

from v2.tasks.utils import updateStatus, resumePipeline
from v2.models import Status, MetadataAssignment, Page, FileType, ProjectMetadataTerm, TextValue
from v2.tasks.text_utils import extractTranscriptionsFromXml, extractTranscriptionFromTxt, handleLinebreakChars


@shared_task()
def extractText(processId: int, options: Dict[str, Any], continuePipeline: bool = True):
    stepKey = "extractText"
    updateStatus(processId, stepKey, Status.IN_PROGRESS)

    # options = {"textTargets": [("prefix", "target1Name", "level"), ("prefix", "targetNName", "level")]}

    for page in Page.objects.filter(item__process__pk=processId):

        lines = []
        if page.fileType == FileType.XML:
            lines = extractTranscriptionsFromXml(Path(page.file.path))
            pass
        elif page.fileType == FileType.PLAINTEXT:
            lines = extractTranscriptionFromTxt(Path(page.file.path))

        text = ""
        for line in lines:
            text += handleLinebreakChars(line)

        for (prefix, standardTerm, level) in options["textTargets"]:
            assignments = MetadataAssignment.objects.filter(
                projectMetadataTerm__metadataTerm__standardTerm=standardTerm,
                projectMetadataTerm__metadataTerm__vocabulary__prefix=prefix, page=page)
            if len(assignments) == 0:
                projectMetadataTerm = ProjectMetadataTerm.objects.filter(metadataTerm__standardTerm=standardTerm,
                                                                         metadataTerm__vocabulary__prefix=prefix,
                                                                         project__pk=page.item.process.project.id).first()
                print(projectMetadataTerm)
                assignment = MetadataAssignment.objects.create(projectMetadataTerm=projectMetadataTerm, page=page)
            else:
                assignment = assignments.first()

            textValues = assignment.textvalue_set.all()
            if len(textValues) == 0:
                TextValue.objects.create(text=text, metadataAssignment=assignment)
            else:
                value = textValues[0]
                value.text = text
                value.save()

    updateStatus(processId, stepKey, Status.COMPLETE)
    if continuePipeline:
        resumePipeline(processId)


@shared_task()
def ner(processId: int, options: Dict[str, Any], continuePipeline: bool = True):
    stepKey = "ner"
    updateStatus(processId, stepKey, Status.IN_PROGRESS)

    # options = {"personTarget": "arab:person", ...}

    updateStatus(processId, stepKey, Status.COMPLETE)
