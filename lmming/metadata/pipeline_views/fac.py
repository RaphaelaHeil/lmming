import datetime
from urllib.parse import urljoin

from django.conf import settings
from django.db import transaction
from django.forms import formset_factory

from metadata.forms.fac import FacManualForm, MintForm, FacFileNameForm, TranslateForm, BatchFacManualForm
from metadata.forms.shared import BatchPageHandleForm
from metadata.models import Status, ProcessingStep, ReportTranslation, Report, FacSpecificData, Page
from metadata.pipeline_views.utils import __fromDisplayList__, fromCommaList
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
                    years = [int(d) for d in fromCommaList(filenameForm.data["date"])]
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
    if not hasattr(job.report, "facspecificdata"):
        data = FacSpecificData.objects.create(report=job.report)
    else:
        data = job.report.facspecificdata
    initial = {"isFormatOf": job.report.isFormatOf, "seriesVolumeName": data.seriesVolumeName,
               "seriesVolumeSignum": data.seriesVolumeSignum}
    if request.method == "POST":
        manualForm = FacManualForm(request.POST, initial=initial)
        if manualForm.is_valid():
            if manualForm.has_changed():
                if "isFormatOf" in manualForm.changed_data:
                    job.report.isFormatOf = manualForm.cleaned_data["isFormatOf"]
                if "seriesVolumeName" in manualForm.changed_data:
                    data.seriesVolumeName = manualForm.cleaned_data["seriesVolumeName"]
                if "seriesVolumeSignum" in manualForm.changed_data:
                    data.seriesVolumeSignum = manualForm.cleaned_data["seriesVolumeSignum"]
                job.report.save()
                data.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.FAC_MANUAL.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": manualForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FAC_MANUAL.label}
    else:
        manualForm = FacManualForm(initial=initial)
        return {"form": manualForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FAC_MANUAL.label}


def mint(request, job):
    initial = {"identifier": job.report.identifier}

    BatchPageFormSet = formset_factory(BatchPageHandleForm, extra=0)
    pageInitial = [{"source": p.source, "bibCitation": p.bibCitation, "pageId": p.pk, "filename": p.originalFileName,
                    "identifier": p.identifier} for p in job.report.page_set.all().order_by("order")]

    if request.method == "POST":
        mintForm = MintForm(request.POST, initial=initial)
        pageForm = BatchPageFormSet(request.POST, initial=pageInitial)
        if mintForm.is_valid() and pageForm.is_valid():
            if mintForm.has_changed():
                if "identifier" in mintForm.changed_data:
                    identifier = mintForm.cleaned_data["identifier"]
                    identifier = identifier.replace("/manifest", "")
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
                processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.MINT_ARKS.label,
                    "pageForm": pageForm}
    else:
        mintForm = MintForm(initial=initial)
        pageForm = BatchPageFormSet(initial=pageInitial)
        return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.MINT_ARKS.label,
                "pageForm": pageForm}


def facTranslate(request, job):
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
        translateForm = TranslateForm(request.POST, initial=initial)
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
                processingStepType=ProcessingStep.ProcessingStepType.FAC_TRANSLATE_TO_SWEDISH.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": translateForm, "job": job,
                    "stepName": ProcessingStep.ProcessingStepType.FAC_TRANSLATE_TO_SWEDISH.label}
    else:
        translateForm = TranslateForm(initial=initial)
        return {"form": translateForm, "job": job,
                "stepName": ProcessingStep.ProcessingStepType.FAC_TRANSLATE_TO_SWEDISH.label}


def bulkFacManual(request, jobIds: str):
    ManualFormSet = formset_factory(BatchFacManualForm, extra=0)

    initial = []
    for report in Report.objects.filter(job__pk__in=jobIds.split(",")).order_by("date"):
        if not hasattr(report, "facspecificdata"):
            data = FacSpecificData.objects.create(report=report)
        else:
            data = report.facspecificdata
        initial.append(
            {"isFormatOf": report.isFormatOf, "reportId": report.id, "date": report.date, "title": report.title,
             "seriesVolumeName": data.seriesVolumeName,
             "seriesVolumeSignum": data.seriesVolumeSignum})

    if request.method == "POST":
        bulkManualForm = ManualFormSet(request.POST, initial=initial)
        if bulkManualForm.is_valid():
            for f in bulkManualForm:
                report = Report.objects.get(pk=f.reportId)
                if f.has_changed():
                    if "isFormatOf" in f.changed_data:
                        report.isFormatOf = f.cleaned_data["isFormatOf"]
                        report.save()
                    if "seriesVolumeName" in f.changed_data:
                        report.facspecificdata.seriesVolumeName = f.cleaned_data["seriesVolumeName"]
                    if "seriesVolumeSignum" in f.changed_data:
                        report.facspecificdata.seriesVolumeSignum = f.cleaned_data["seriesVolumeSignum"]
                    report.facspecificdata.save()
                job = report.job
                step = job.processingSteps.filter(
                    processingStepType=ProcessingStep.ProcessingStepType.FAC_MANUAL.value).first()
                step.status = Status.COMPLETE
                step.save()
                transaction.on_commit(lambda: scheduleTask(job.pk))
            return {}
        else:
            return {"form": bulkManualForm, "jobIds": jobIds,
                    "stepName": ProcessingStep.ProcessingStepType.FAC_MANUAL.value.lower()}
    else:
        bulkManualForm = ManualFormSet(initial=initial)
        return {"form": bulkManualForm, "jobIds": jobIds,
                "stepName": ProcessingStep.ProcessingStepType.FAC_MANUAL.value.lower()}
