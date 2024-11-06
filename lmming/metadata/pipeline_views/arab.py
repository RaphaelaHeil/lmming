import datetime
from datetime import date
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction

from metadata.forms.arab import ArabGenerateForm, ArabManualForm, ArabMintForm, ArabFileNameForm
from metadata.forms.fac import MintForm
from metadata.models import Status, ProcessingStep
from metadata.pipeline_views.utils import __fromDisplayList__
from metadata.tasks.manage import scheduleTask


def arabFilename(request, job):
    # add a check that the user is allowed to see/modify this view? otherwise return general job view?
    if request.method == "POST":
        filenameForm = ArabFileNameForm(request.POST, initial={"organisationID": job.report.unionId,
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
            return {"job": job}
        else:
            return {"form": filenameForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILENAME.label}
    else:
        filenameForm = ArabFileNameForm(initial={"organisationID": job.report.unionId, "type": job.report.type,
                                                 "date": job.report.get_date_display()})
        return {"form": filenameForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILENAME.label}


def arabGenerate(request, job):
    initial = {"title": job.report.title, "created": job.report.created.year if job.report.created else "",
               "available": job.report.available, "language": job.report.get_language_display(),
               "license": job.report.get_license_display(), "source": job.report.get_source_display(),
               "accessRights": job.report.accessRights, "isFormatOf": job.report.isFormatOf}
    if request.method == "POST":
        computeForm = ArabGenerateForm(request.POST, initial=initial)
        if computeForm.is_valid():
            if computeForm.has_changed():
                if "title" in computeForm.changed_data:
                    job.report.title = computeForm.cleaned_data["title"]
                if "created" in computeForm.changed_data:
                    job.report.created = date(int(computeForm.cleaned_data["created"]), month=1, day=1)
                if "available" in computeForm.changed_data:
                    job.report.available = computeForm.cleaned_data["available"]
                if "language" in computeForm.changed_data:
                    job.report.language = __fromDisplayList__(computeForm.cleaned_data["language"])
                if "license" in computeForm.changed_data:
                    job.report.license = __fromDisplayList__(computeForm.cleaned_data["license"])
                if "source" in computeForm.changed_data:
                    job.report.source = __fromDisplayList__(computeForm.cleaned_data["source"])
                if "accessRights" in computeForm.changed_data:
                    job.report.accessRights = computeForm.cleaned_data["accessRights"]
                if "isFormatOf" in computeForm.changed_data:
                    job.report.isFormatOf = computeForm.cleaned_data["isFormatOf"]
                job.report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": computeForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_GENERATE.label}
    else:
        computeForm = ArabGenerateForm(initial=initial)
        return {"form": computeForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_GENERATE.label}


def arabManual(request, job):
    initial = {"description": job.report.description, "reportType": job.report.type}
    if request.method == "POST":
        imageForm = ArabManualForm(request.POST, initial=initial)
        if imageForm.is_valid():
            if imageForm.has_changed():
                if "description" in imageForm.changed_data:
                    job.report.description = imageForm.cleaned_data["description"]
                if "reportType" in imageForm.changed_data:
                    job.report.type = imageForm.cleaned_data["reportType"]
                job.report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.ARAB_MANUAL.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": imageForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_MANUAL.label}
    else:
        imageForm = ArabManualForm(initial=initial)
        return {"form": imageForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_MANUAL.label}


def arabMint(request, job):
    initial = {"identifier": job.report.identifier}
    if request.method == "POST":
        mintForm = ArabMintForm(request.POST, initial=initial)
        if mintForm.is_valid():
            if mintForm.has_changed():
                if "identifier" in mintForm.changed_data:
                    identifier = mintForm.cleaned_data["identifier"]
                    identifier = identifier.replace("?urlappend=/manifest", "")
                    identifier = identifier.strip("/")

                    job.report.identifier = identifier
                    job.report.noid = identifier.split("/")[-1]
                    job.report.save()

                    for page in job.report.page_set.all():
                        page.iiifId = f"{job.report.noid}_{page.order}"
                        page.identifier = urljoin(settings.IIIF_BASE_URL, f"iiif/image/{page.iiifId}/info.json")
                        page.save()

            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.label}
    else:
        mintForm = MintForm(initial=initial)
        return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.label}


def arabTranslate(request, job):
    pass