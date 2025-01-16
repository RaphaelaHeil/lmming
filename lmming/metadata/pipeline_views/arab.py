import datetime
from datetime import date
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction

from metadata.forms.arab import ArabGenerateForm, ArabManualForm, ArabMintForm, ArabFileNameForm, ArabTranslateForm
from metadata.forms.shared import BatchPageHandleForm
from metadata.models import Status, ProcessingStep, ReportTranslation, Report, Page
from metadata.pipeline_views.utils import __fromDisplayList__
from metadata.tasks.manage import scheduleTask
from django.forms import formset_factory


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
    initial = {"created": job.report.created.year if job.report.created else "",
               "available": job.report.available, "language": job.report.get_language_display(),
               "license": job.report.get_license_display(), "source": job.report.get_source_display(),
               "accessRights": job.report.accessRights, "isFormatOf": job.report.isFormatOf}
    if request.method == "POST":
        computeForm = ArabGenerateForm(request.POST, initial=initial)
        if computeForm.is_valid():
            if computeForm.has_changed():
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
    report = job.report
    translation = report.reporttranslation_set.filter(language="sv")
    if not translation:
        translation = ReportTranslation(language="sv", report=report)
    else:
        translation = translation.first()
    initial = {"description": job.report.description, "reportType": job.report.type,
               "descriptionSv": translation.description, "title": report.title}
    if request.method == "POST":
        imageForm = ArabManualForm(request.POST, initial=initial)
        if imageForm.is_valid():
            if imageForm.has_changed():
                if "title" in imageForm.changed_data:
                    report.title = imageForm.cleaned_data["title"]
                if "description" in imageForm.changed_data:
                    report.description = imageForm.cleaned_data["description"]
                if "reportType" in imageForm.changed_data:
                    report.type = imageForm.cleaned_data["reportType"]
                if "descriptionSv" in imageForm.changed_data:
                    translation.description = imageForm.cleaned_data["descriptionSv"]
                translation.save()
                report.save()
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

    BatchPageFormSet = formset_factory(BatchPageHandleForm, extra=0)
    pageInitial = [{"source": p.source, "bibCitation": p.bibCitation, "pageId": p.pk, "filename": p.originalFileName,
                    "identifier": p.identifier} for p in job.report.page_set.all().order_by("order")]

    if request.method == "POST":
        mintForm = ArabMintForm(request.POST, initial=initial)
        pageForm = BatchPageFormSet(request.POST, initial=pageInitial)
        if mintForm.is_valid() and pageForm.is_valid():
            if mintForm.has_changed():
                if "identifier" in mintForm.changed_data:
                    identifier = mintForm.cleaned_data["identifier"]
                    identifier = identifier.replace("?urlappend=/manifest", "")
                    identifier = identifier.strip("/")

                    job.report.identifier = identifier
                    job.report.noid = identifier.split("/")[-1]
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
                processingStepType=ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.label,
                    "pageForm": pageForm}
    else:
        mintForm = ArabMintForm(initial=initial)
        pageForm = BatchPageFormSet(initial=pageInitial)
        return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.label,
                "pageForm": pageForm}


def arabTranslate(request, job):
    report = job.report
    translation = report.reporttranslation_set.filter(language="sv")
    if not translation:
        translation = ReportTranslation(language="sv", report=report)
    else:
        translation = translation.first()
    initial = {"coverage": translation.coverage, "type": translation.type, "isFormatOf": translation.isFormatOf,
               "accessRights": translation.accessRights, "description": translation.description,
               "coverageEN": Report.UnionLevel[report.coverage].label, "typeEN": report.get_type_display(),
               "isFormatOfEN": report.get_isFormatOf_display(),
               "accessRightsEN": Report.AccessRights[report.accessRights].label, "descriptionEN": report.description}

    if request.method == "POST":
        translateForm = ArabTranslateForm(request.POST, initial=initial)
        if translateForm.is_valid():
            if translateForm.has_changed():
                if "coverage" in translateForm.changed_data:
                    translation.coverage = translateForm.cleaned_data["coverage"]
                if "type" in translateForm.changed_data:
                    translation.type = translateForm.cleaned_data["type"]
                if "isFormatOf" in translateForm.changed_data:
                    translation.isFormatOf = translateForm.cleaned_data["isFormatOf"]
                if "accessRights" in translateForm.changed_data:
                    translation.accessRights = translateForm.cleaned_data["accessRights"]
                if "description" in translateForm.changed_data:
                    translation.description = translateForm.cleaned_data["description"]

            translation.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.ARAB_TRANSLATE_TO_SWEDISH.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": translateForm, "job": job,
                    "stepName": ProcessingStep.ProcessingStepType.ARAB_TRANSLATE_TO_SWEDISH.label}
    else:
        translateForm = ArabTranslateForm(initial=initial)
        return {"form": translateForm, "job": job,
                "stepName": ProcessingStep.ProcessingStepType.ARAB_TRANSLATE_TO_SWEDISH.label}
