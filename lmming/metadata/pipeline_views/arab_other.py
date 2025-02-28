from datetime import date

from django.db import transaction
from django.forms import formset_factory

from metadata.forms.arab_other import ArabOtherFilemakerForm, ArabOtherMintForm, ArabOtherManualForm, \
    ArabOtherFileNameForm
from metadata.forms.shared import BatchPageHandleForm
from metadata.models import Status, ProcessingStep, ReportTranslation, Page
from metadata.pipeline_views.utils import fromCommaList
from metadata.tasks.manage import scheduleTask


def __dateDisplay(d):
    if d:
        return d.strftime("%Y-%m-%d")
    else:
        return ""

def __fromDateDisplay(d:str):
    day = 1
    month = 1
    s = d.split("-")
    if len(s) > 2:
        day = int(s[2])
    if len(s) > 1:
        month = int(s[1])
    year = int(s[0])
    return date(year=year, month=month, day=day)


def filemakerLookupArab(request, job):
    initial = {"creator": job.report.creator}
    if request.method == "POST":
        filemakerForm = ArabOtherFilemakerForm(request.POST, initial=initial)
        if filemakerForm.is_valid():
            if filemakerForm.has_changed():
                if "creator" in filemakerForm.changed_data:
                    job.report.creator = filemakerForm.cleaned_data["creator"]
                job.report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP_ARAB.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": filemakerForm, "job": job,
                    "stepName": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP_ARAB.label}
    else:
        filemakerForm = ArabOtherFilemakerForm(initial=initial)
        return {"form": filemakerForm, "job": job,
                "stepName": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP_ARAB.label}


def arabOtherManual(request, job):
    report = job.report
    initial = {"title": report.title, "source": report.get_source_display(), "description": report.description,
               "date": ",".join([__dateDisplay(d) for d in report.date]),
               "created": __dateDisplay(report.created), "format": report.get_format_display(),
               "accessRights": report.accessRights, "license": report.get_license_display(), "comment": report.comment,
               "spatial": report.get_spatial_display(), "medium": report.get_medium_display(),
               "language": report.get_language_display()}
    if request.method == "POST":
        imageForm = ArabOtherManualForm(request.POST, initial=initial)
        if imageForm.is_valid():
            if imageForm.has_changed():
                if "title" in imageForm.changed_data:
                    report.title = imageForm.cleaned_data["title"]
                if "source" in imageForm.changed_data:
                    report.source = fromCommaList(imageForm.cleaned_data["source"])
                if "description" in imageForm.changed_data:
                    report.description = imageForm.cleaned_data["description"]
                if "date" in imageForm.changed_data:
                    report.date = [__fromDateDisplay(d) for d in fromCommaList(imageForm.data["date"])]
                if "created" in imageForm.changed_data:
                    report.created = __fromDateDisplay(imageForm.cleaned_data["created"])
                if "format" in imageForm.changed_data:
                    report.format = __fromDateDisplay(imageForm.cleaned_data["format"])
                if "accessRights" in imageForm.changed_data:
                    report.accessRights = imageForm.cleaned_data["accessRights"]  # TODO: radio button
                if "license" in imageForm.changed_data:
                    report.license = fromCommaList(imageForm.cleaned_data["license"])
                if "comment" in imageForm.changed_data:
                    report.comment = imageForm.cleaned_data["comment"]
                if "spatial" in imageForm.changed_data:
                    report.spatial = fromCommaList(imageForm.cleaned_data["spatial"])
                if "medium" in imageForm.changed_data:
                    report.medium = __fromDateDisplay(imageForm.cleaned_data["medium"])
                if "language" in imageForm.changed_data:
                    report.language = fromCommaList(imageForm.cleaned_data["language"])
                report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.ARAB_OTHER_MANUAL.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": imageForm, "job": job,
                    "stepName": ProcessingStep.ProcessingStepType.ARAB_OTHER_MANUAL.label}
    else:
        imageForm = ArabOtherManualForm(initial=initial)
        return {"form": imageForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_OTHER_MANUAL.label}


def arabOtherMintHandle(request, job):
    initial = {"identifier": job.report.identifier, "references": job.report.references}

    BatchPageFormSet = formset_factory(BatchPageHandleForm, extra=0)
    pageInitial = [{"source": p.source, "bibCitation": p.bibCitation, "pageId": p.pk, "filename": p.originalFileName,
                    "identifier": p.identifier} for p in job.report.page_set.all().order_by("order")]

    if request.method == "POST":
        mintForm = ArabOtherMintForm(request.POST, initial=initial)
        pageForm = BatchPageFormSet(request.POST, initial=pageInitial)
        if mintForm.is_valid() and pageForm.is_valid():
            if mintForm.has_changed():
                if "identifier" in mintForm.changed_data:
                    identifier = mintForm.cleaned_data["identifier"]
                    identifier = identifier.replace("?urlappend=/manifest", "")
                    identifier = identifier.strip("/")
                    job.report.identifier = identifier
                    job.report.noid = identifier.split("/")[-1]
                if "references" in mintForm.changed_data:
                    references = mintForm.cleaned_data["references"]
                    references = references.rstrip("/")
                    referencesNoid = references.split("/")[-1]
                    job.report.references = references
                    job.report.referencesNoid = referencesNoid
                job.report.save()

            for f in pageForm:
                if f.has_changed():
                    page = Page.objects.get(pk=f.pageId)
                    page.identifier = f.cleaned_data["identifier"]
                    page.source = f.cleaned_data["source"]
                    page.bibCitation = f.cleaned_data["bibCitation"]
                    page.noid = ""
                    page.iiifId = ""
                    page.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.ARAB_OTHER_MINT_HANDLE.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": mintForm, "job": job,
                    "stepName": ProcessingStep.ProcessingStepType.ARAB_OTHER_MINT_HANDLE.label,
                    "pageForm": pageForm}
    else:
        mintForm = ArabOtherMintForm(initial=initial)
        pageForm = BatchPageFormSet(initial=pageInitial)
        return {"form": mintForm, "job": job,
                "stepName": ProcessingStep.ProcessingStepType.ARAB_OTHER_MINT_HANDLE.label,
                "pageForm": pageForm}


def arabOtherFilename(request, job):
    # add a check that the user is allowed to see/modify this view? otherwise return general job view?
    if request.method == "POST":
        filenameForm = ArabOtherFileNameForm(request.POST, initial={"organisationID": job.report.unionId,
                                                                    "type": job.report.type,
                                                                    "date": job.report.get_date_display()})
        if filenameForm.is_valid():
            if filenameForm.has_changed():
                if "organisationID" in filenameForm.changed_data:
                    job.report.unionId = filenameForm.cleaned_data["organisationID"]
                if "type" in filenameForm.changed_data:
                    job.report.type = filenameForm.cleaned_data["type"]
                if "date" in filenameForm.changed_data:
                    years = [int(d) for d in fromCommaList(filenameForm.data["date"])]
                    job.report.date = [date(year=y, month=1, day=1) for y in years]
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
        filenameForm = ArabOtherFileNameForm(initial={"organisationID": job.report.unionId, "type": job.report.type,
                                                      "date": job.report.get_date_display()})
        return {"form": filenameForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILENAME.label}
