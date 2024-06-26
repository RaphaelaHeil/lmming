from datetime import date

import pandas as pd
from django.db.models import Q
from django.http import QueryDict, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect

from metadata.enum_utils import PipelineStepName
from metadata.forms import ExtractionTransferDetailForm, ExtractionTransferSettingsForm, SettingsForm, \
    FilemakerSettingsForm
from metadata.lookup import URL_STEP_INDEX
from metadata.models import ExtractionTransfer, Report, Page, Status, Job, ProcessingStep, DefaultValueSettings, \
    DefaultNumberSettings
from metadata.tasks import restartTask
from metadata.tasks import scheduleTask
from metadata.utils import parseFilename, buildReportIdentifier, updateFilemakerData


def restart(request, job_id: int, step: str):
    stepLookup = {"filename": ProcessingStep.ProcessingStepType.FILENAME,
                  "filemaker": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP,
                  "generate": ProcessingStep.ProcessingStepType.GENERATE, "ner": ProcessingStep.ProcessingStepType.NER,
                  "mint": ProcessingStep.ProcessingStepType.MINT_ARKS}

    restartTask(job_id, stepLookup[step])
    return redirect("metadata:job", job_id=job_id)


def batchDeleteModal(request):
    ids = [int(id) for id in (QueryDict(request.body).getlist("ids"))]
    print(ids)
    result = ""
    if ids:
        result = f"ids={ids[0]}"
        for ID in ids[1:]:
            result += f"&ids={ID}"
    return render(request, "modal/bulk_delete.html",
                  {"ids": result, "jobs": (ExtractionTransfer.objects.filter(id__in=ids))})


def deleteModal(request, transfer_id):
    transfer = get_object_or_404(ExtractionTransfer, pk=transfer_id)
    return render(request, "modal/delete_transfer.html", {"transfer": transfer})


def settingsModal(request):
    language = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE).first()
    license = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE).first()
    source = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE).first()
    accessRights = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.DC_ACCESS_RIGHTS).first()
    avilableYearOffset = DefaultNumberSettings.objects.filter(
        pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET).first()
    initial = {"language": language.value if language else "",
               "license": license.value if license else "",
               "source": source.value if source else "",
               "accessRights": accessRights.value if accessRights else "",
               "avilableYearOffset": avilableYearOffset.value if avilableYearOffset else 0
               }
    if request.method == 'POST':
        settingsForm = SettingsForm(request.POST, initial=initial)
        filemakerForm = FilemakerSettingsForm(request.POST, request.FILES)
        if settingsForm.is_valid():
            if settingsForm.has_changed():
                if "language" in settingsForm.changed_data:
                    if language:
                        language.value = settingsForm.cleaned_data["language"]
                        language.save()
                    else:
                        DefaultValueSettings.objects.create(
                            pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE,
                            value=settingsForm.cleaned_data["language"])
                if "license" in settingsForm.changed_data:
                    if license:
                        license.value = settingsForm.cleaned_data["license"]
                        license.save()
                    else:
                        DefaultValueSettings.objects.create(
                            pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE,
                            value=settingsForm.cleaned_data["license"])
                if "source" in settingsForm.changed_data:
                    if source:
                        source.value = settingsForm.cleaned_data["source"]
                        source.save()
                    else:
                        DefaultValueSettings.objects.create(
                            pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE,
                            value=settingsForm.cleaned_data["source"])
                if "accessRights" in settingsForm.changed_data:
                    if accessRights:
                        accessRights.value = settingsForm.cleaned_data["accessRights"]
                        accessRights.save()
                    else:
                        DefaultValueSettings.objects.create(
                            pk=DefaultValueSettings.DefaultValueSettingsType.DC_ACCESS_RIGHTS,
                            value=settingsForm.cleaned_data["accessRights"])
                if "avilableYearOffset" in settingsForm.changed_data:
                    if avilableYearOffset:
                        avilableYearOffset.value = settingsForm.cleaned_data["avilableYearOffset"]
                        avilableYearOffset.save()
                    else:
                        DefaultNumberSettings.objects.create(
                            pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET,
                            value=settingsForm.cleaned_data["avilableYearOffset"])
        if filemakerForm.is_valid():
            filemakerCsv = filemakerForm.cleaned_data["filemaker_csv"]
            if filemakerCsv:
                updateFilemakerData(pd.read_csv(filemakerCsv))  # TODO: technically needs a loading indicator ...
        else:
            pass  # TODO: return error or smth
        return redirect("/")
    else:
        return render(request, 'modal/settings.html',
                      {"form": SettingsForm(initial=initial), "filemaker": FilemakerSettingsForm()})


def verifyTransfer(request, transfer_id):
    transferInstance = get_object_or_404(ExtractionTransfer, pk=transfer_id)

    if request.method == "POST":
        for job in transferInstance.jobs.all():
            scheduleTask(job.pk)
        # TODO: add delete button,
        return redirect("/")

    return render(request, "partial/verify_transfer.html", {"transfer": transferInstance})


def __buildProcessingSteps__(data, job):
    steps = []
    stepKeys = [("filenameMode", "filenameHumVal", PipelineStepName.FILENAME),
                ("filemakerMode", "filemakerHumVal", PipelineStepName.FILEMAKER_LOOKUP),
                ("generateMode", "generateHumVal", PipelineStepName.GENERATE),
                # ("imageMode", "imageHumVal", PipelineStepName.IMAGE),
                ("facManualMode", "facManualHumVal", PipelineStepName.FAC_MANUAL),
                ("nerMode", "nerHumVal", PipelineStepName.NER),
                ("mintMode", "mintHumVal", PipelineStepName.MINT_ARKS)]

    for mode, humVal, stepName in stepKeys:
        p = ProcessingStep.objects.create(job=job, order=stepName.value[0],
                                          processingStepType=ProcessingStep.ProcessingStepType[stepName.name],
                                          humanValidation=data[humVal], mode=data[mode])
        steps.append(p)
    return steps


def createTransfer(request):
    detailform = ExtractionTransferDetailForm()
    extractionSettingsForm = ExtractionTransferSettingsForm()
    if request.method == 'POST':
        detailform = ExtractionTransferDetailForm(request.POST, request.FILES)
        extractionSettingsForm = ExtractionTransferSettingsForm(request.POST)

        if detailform.is_valid() and extractionSettingsForm.is_valid():
            collectionName = detailform.cleaned_data['processName']
            transferInstance = ExtractionTransfer.objects.create(name=collectionName,
                                                                 status=Status.AWAITING_HUMAN_VALIDATION)
            transcriptionFiles = detailform.cleaned_data["file_field"]
            pagesToReports = {}
            for file in transcriptionFiles:
                originalFilename = str(file)
                try:
                    data = parseFilename(originalFilename)
                    data["file"] = file
                    reportIdentifier = buildReportIdentifier(data)
                    if reportIdentifier not in pagesToReports:
                        pagesToReports[reportIdentifier] = []

                    pagesToReports[reportIdentifier].append(data)
                except SyntaxError as e:
                    # TODO
                    pass

            processingSteps = []

            for reportIdentifier in pagesToReports:
                pages = pagesToReports[reportIdentifier]
                unionId = {p["union_id"] for p in pages}.pop()
                reportType = list({p["type"] for p in pages})
                dateList = list({date(p["date"], 1, 1) for p in pages})

                r = Report.objects.create(transfer=transferInstance, unionId=unionId, type=reportType, date=dateList)

                for page in pages:
                    Page.objects.create(report=r, order=int(page["page"]), transcriptionFile=page["file"],
                                        originalFileName=page["file"])

                j = Job.objects.create(transfer=transferInstance, report=r)
                if not processingSteps:
                    processingSteps = __buildProcessingSteps__(extractionSettingsForm.cleaned_data, j)
                else:
                    for step in processingSteps:
                        step.pk = None
                        step._state.adding = True
                        step.job = j
                        step.save()
                r.job = j
                r.save()

            return redirect("metadata:verify_transfer", transfer_id=transferInstance.pk)

    return render(request, 'partial/create_transfer.html',
                  {"detailform": detailform, "settings": extractionSettingsForm})


def awaitingHumanInteraction(request):
    stepData = []
    jobPks = set()
    processingSteps = ProcessingStep.objects.filter(
        Q(status=Status.AWAITING_HUMAN_VALIDATION) | Q(status=Status.AWAITING_HUMAN_INPUT))
    for step in processingSteps:
        if step.job.pk in jobPks:
            continue
        jobPks.add(step.job.pk)
        stepData.append(
            {"stepName": URL_STEP_INDEX[step.processingStepType], "processName": step.job.transfer.name,
             "stepDisplay": ProcessingStep.ProcessingStepType[step.processingStepType].label,
             "status": Status[step.status].label, "job": step.job.pk, "startDate": step.job.startDate})

    return render(request, 'partial/waiting_jobs_table.html', {"steps": stepData})


def waitingCount(request):
    value = Job.objects.filter(
        Q(status=Status.AWAITING_HUMAN_VALIDATION) | Q(status=Status.AWAITING_HUMAN_INPUT)).count()
    if value == 0:
        return HttpResponse("")
    else:
        return HttpResponse(str(value))
