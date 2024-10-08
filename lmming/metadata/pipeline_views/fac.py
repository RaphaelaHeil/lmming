import datetime

from django.db import transaction

from metadata.forms.fac import FacManualForm, MintForm, FacFileNameForm
from metadata.models import Status, ProcessingStep
from metadata.pipeline_views.utils import __fromDisplayList__
from metadata.tasks.manage import scheduleTask


def facFilename(request, job):
    # add a check that the user is allowed to see/modify this view? otherwise return general job view?
    if request.method == "POST":
        filenameForm = FacFileNameForm(request.POST, initial={"organisationID": job.report.unionId,
                                                              "type": job.report.type,
                                                              "date": job.report.get_date_display()})
        if filenameForm.is_valid():
            if filenameForm.has_changed():
                if "organisationID" in filenameForm.changed_data:
                    job.report.unionId = filenameForm.cleaned_data["organisationID"]
                if "type" in filenameForm.changed_data:
                    job.report.type = filenameForm.cleaned_data["type"]
                if "date" in filenameForm.changed_data:
                    years = [int(d) for d in __fromDisplayList__(filenameForm.data["date"])]
                    job.report.date = [datetime.date(year=y, month=1, day=1) for y in years]
                job.report.save()

            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.FILENAME.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}  # TODO: double-check this return type ...
        else:
            return {"form": filenameForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILENAME.label}
    else:
        filenameForm = FacFileNameForm(initial={"organisationID": job.report.unionId, "type": job.report.type,
                                                "date": job.report.get_date_display()})
        return {"form": filenameForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILENAME.label}


def facManual(request, job):
    initial = {"isFormatOf": job.report.isFormatOf}
    if request.method == "POST":
        imageForm = FacManualForm(request.POST, initial=initial)
        if imageForm.is_valid():
            if imageForm.has_changed():
                if "isFormatOf" in imageForm.changed_data:
                    job.report.isFormatOf = imageForm.cleaned_data["isFormatOf"]
                job.report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.FAC_MANUAL.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": imageForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FAC_MANUAL.label}
    else:
        imageForm = FacManualForm(initial=initial)
        return {"form": imageForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FAC_MANUAL.label}


def mint(request, job):
    initial = {"identifier": job.report.identifier}
    if request.method == "POST":
        mintForm = MintForm(request.POST, initial=initial)
        if mintForm.is_valid():
            if mintForm.has_changed():
                if "identifier" in mintForm.changed_data:
                    job.report.identifier = mintForm.cleaned_data["identifier"]
                # TDOD: fix this field! (noid vs identifier, etc)
                job.report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.MINT_ARKS.label}
    else:
        mintForm = MintForm(initial=initial)
        return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.MINT_ARKS.label}
