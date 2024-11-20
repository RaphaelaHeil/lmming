from copy import deepcopy

import pandas as pd
from django.conf import settings
from django.db.models import Q
from django.forms import formset_factory
from django.http import QueryDict, HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from metadata.forms.shared import ExtractionTransferDetailForm, SettingsForm, ExternalRecordsSettingsForm, \
    ProcessingStepForm
from metadata.models import ExtractionTransfer, Report, Page, Status, Job, ProcessingStep, DefaultValueSettings, \
    DefaultNumberSettings
from metadata.pipeline_views.fac import bulkFacManual
from metadata.tasks.manage import restartTask, scheduleTask
from metadata.utils import parseFilename, buildReportIdentifier, updateExternalRecords, buildProcessingSteps

FAC_PROCESSING_STEP_INITIAL = [{"label": ProcessingStep.ProcessingStepType.FILENAME,
                                "tooltip": "Extracts 'date' and 'type' information, as well as the organisation's id, "
                                           "from the filename.", "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC,
                                "humanValidation": False, "modeDisabled": False},
                               {"label": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP,
                                "tooltip": "Uses the organisation's ID to extract informationen from Filemaker-based "
                                           "data. Fills the fields 'creator', 'relation', 'coverage', and 'spatial'.",
                                "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                "modeDisabled": False},
                               {"label": ProcessingStep.ProcessingStepType.GENERATE,
                                "tooltip": "Fills the fields 'title', 'created', 'description' and 'available', based "
                                           "on information collected in the previous two steps.",
                                "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                "modeDisabled": False},
                               {"label": ProcessingStep.ProcessingStepType.FAC_MANUAL,
                                "tooltip": "Any piece of data that can not be handled automatically at the moment.",
                                "mode": ProcessingStep.ProcessingStepMode.MANUAL, "humanValidation": False,
                                "modeDisabled": True},
                               {"label": ProcessingStep.ProcessingStepType.NER,
                                "tooltip": "Extracts named entities from the provided transcriptions.",
                                "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                "modeDisabled": False},
                               {"label": ProcessingStep.ProcessingStepType.MINT_ARKS,
                                "tooltip": "Mints ARKs for IIIF and AtoM, to be included in the CSV for Omeka.",
                                "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                "modeDisabled": False},
                               {"label": ProcessingStep.ProcessingStepType.FAC_TRANSLATE_TO_SWEDISH,
                                "tooltip": "Translate coverage, type, isFormatOf and accessRights to Swedish",
                                "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                "modeDisabled": False}
                               ]

ARAB_PROCESSING_STEP_INITIAL = [{"label": ProcessingStep.ProcessingStepType.FILENAME,
                                 "tooltip": "Extracts 'date' and 'type' information, as well as the organisation's id, "
                                            "from the filename.", "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC,
                                 "humanValidation": False, "modeDisabled": False},
                                {"label": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP,
                                 "tooltip": "Uses the organisation's ID to extract informationen from Filemaker-based "
                                            "data. Fills the fields 'creator', 'relation', 'coverage', and 'spatial'.",
                                 "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                 "modeDisabled": False},
                                {"label": ProcessingStep.ProcessingStepType.ARAB_GENERATE,
                                 "tooltip": "Fills in the fields 'created', 'available', 'accessRights', "
                                            "'language', 'license', 'source', and 'isFormatOf' based on information, "
                                            "collected in the previous steps.",
                                 "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                 "modeDisabled": False},
                                {"label": ProcessingStep.ProcessingStepType.ARAB_MANUAL,
                                 "tooltip": "Any piece of data that can not be handled automatically at the moment.",
                                 "mode": ProcessingStep.ProcessingStepMode.MANUAL, "humanValidation": False,
                                 "modeDisabled": True},
                                {"label": ProcessingStep.ProcessingStepType.NER,
                                 "tooltip": "Extracts named entities from the provided transcriptions.",
                                 "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                 "modeDisabled": False},
                                {"label": ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE,
                                 "tooltip": "Creates and registers a new handle for each report.",
                                 "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                 "modeDisabled": False},
                                {"label": ProcessingStep.ProcessingStepType.ARAB_TRANSLATE_TO_SWEDISH,
                                 "tooltip": "Translate coverage, type, isFormatOf and accessRights to Swedish",
                                 "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False,
                                 "modeDisabled": False}
                                ]


def restart(_request, job_id: int, step: str):
    restartTask(job_id, ProcessingStep.ProcessingStepType[step.upper()])
    return redirect("metadata:job", job_id=job_id)


def batchDeleteModal(request):
    ids = [int(id) for id in (QueryDict(request.body).getlist("ids"))]
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


def cancelTransferModal(request, transfer_id):
    transfer = get_object_or_404(ExtractionTransfer, pk=transfer_id)
    return render(request, "modal/cancel_transfer.html", {"transfer": transfer})


def settingsModal(request):
    language = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE).first()
    license = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE).first()
    source = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE).first()
    avilableYearOffset = DefaultNumberSettings.objects.filter(
        pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET).first()
    normalisationYearCutOff = DefaultNumberSettings.objects.filter(
        pk=DefaultNumberSettings.DefaultNumberSettingsType.NER_NORMALISATION_END_YEAR).first()
    initial = {"language": language.value if language else "",
               "license": license.value if license else "",
               "source": source.value if source else "",
               "avilableYearOffset": avilableYearOffset.value if avilableYearOffset else 0,
               "normalisationYearCutOff": normalisationYearCutOff.value if normalisationYearCutOff else 1900
               }
    if request.method == 'POST':
        settingsForm = SettingsForm(request.POST, initial=initial)
        filemakerForm = ExternalRecordsSettingsForm(request.POST, request.FILES)
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
                if "avilableYearOffset" in settingsForm.changed_data:
                    if avilableYearOffset:
                        avilableYearOffset.value = settingsForm.cleaned_data["avilableYearOffset"]
                        avilableYearOffset.save()
                    else:
                        DefaultNumberSettings.objects.create(
                            pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET,
                            value=settingsForm.cleaned_data["avilableYearOffset"])
                if "normalisationYearCutOff" in settingsForm.changed_data:
                    if normalisationYearCutOff:
                        normalisationYearCutOff.value = settingsForm.cleaned_data["normalisationYearCutOff"]
                        normalisationYearCutOff.save()
                    else:
                        DefaultNumberSettings.objects.create(
                            pk=DefaultNumberSettings.DefaultNumberSettingsType.NER_NORMALISATION_END_YEAR,
                            value=settingsForm.cleaned_data["normalisationYearCutOff"])

        if filemakerForm.is_valid():
            filemakerCsv = filemakerForm.cleaned_data["externalRecordCsv"]
            if filemakerCsv:
                updateExternalRecords(pd.read_csv(filemakerCsv))  # TODO: technically needs a loading indicator ...
        else:
            pass  # TODO: return error or smth
        return redirect("/")
    else:
        return render(request, 'modal/settings.html',
                      {"form": SettingsForm(initial=initial), "filemaker": ExternalRecordsSettingsForm()})


def verifyTransfer(request, transfer_id):
    transferInstance = get_object_or_404(ExtractionTransfer, pk=transfer_id)

    if request.method == "POST":
        for job in transferInstance.jobs.all():
            scheduleTask(job.pk)
        # TODO: add delete button,
        return redirect("/")

    return render(request, "partial/verify_transfer.html", {"transfer": transferInstance})


def createTransfer(request):
    detailform = ExtractionTransferDetailForm()
    StepFormSet = formset_factory(ProcessingStepForm, extra=0)

    if settings.ARCHIVE_INST == "FAC":
        initial = deepcopy(FAC_PROCESSING_STEP_INITIAL)
    else:
        initial = deepcopy(ARAB_PROCESSING_STEP_INITIAL)

    if request.method == 'POST':
        detailform = ExtractionTransferDetailForm(request.POST, request.FILES)
        stepForm = StepFormSet(request.POST, initial=initial)

        if detailform.is_valid() and stepForm.is_valid():
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
                except SyntaxError as _e:
                    # TODO
                    pass

            for reportIdentifier in pagesToReports:
                pages = pagesToReports[reportIdentifier]
                unionId = set(p["union_id"] for p in pages).pop()  # TODO: can there be multiple?
                reportType = list(set(p["type"] for p in pages))

                dates = set()
                for p in pages:
                    dates.update(p["date"])
                dateList = sorted(list(dates))

                if settings.ARCHIVE_INST == "FAC":
                    r = Report.objects.create(transfer=transferInstance, unionId=unionId, type=reportType,
                                              date=dateList)
                else:
                    r = Report.objects.create(transfer=transferInstance, unionId=unionId, date=dateList)
                Page.objects.bulk_create([Page(report=r, order=int(page["page"]), transcriptionFile=page["file"],
                                               originalFileName=page["file"]) for page in pages])

                j = Job.objects.create(transfer=transferInstance, report=r)

                config = []
                for f in stepForm:
                    config.append({"stepType": f.label, "mode": f.cleaned_data["mode"],
                                   "humanValidation": f.cleaned_data["humanValidation"]})

                buildProcessingSteps(config, j)
                r.job = j
                r.save()

            return redirect("metadata:verify_transfer", transfer_id=transferInstance.pk)

    stepForm = StepFormSet(initial=initial)
    return render(request, 'partial/create_transfer.html', {"detailform": detailform, "steps": stepForm})


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
            {"stepName": step.processingStepType.lower(), "processName": step.job.transfer.name,
             "stepDisplay": ProcessingStep.ProcessingStepType[step.processingStepType].label,
             "status": Status[step.status].label, "job": step.job.pk, "startDate": step.job.startDate})

    return render(request, 'partial/waiting_jobs_table.html', {"steps": stepData})


def waitingProcesses(request):
    processData = []

    processingSteps = ProcessingStep.objects.filter(
        Q(processingStepType=ProcessingStep.ProcessingStepType.FAC_MANUAL.value) & (
                Q(status=Status.AWAITING_HUMAN_VALIDATION) | Q(status=Status.AWAITING_HUMAN_INPUT)))
    transfers = {}
    for step in processingSteps:
        p = step.job.transfer
        if p.name not in transfers:
            transfers[p.name] = {"stepName": ProcessingStep.ProcessingStepType[step.processingStepType].label,
                                 "status": Status[step.status].label, "count": 1,
                                 "total": step.job.transfer.jobs.count(), "jobs": [str(step.job.pk)],
                                 "stepUrl": step.processingStepType.lower()}
        else:
            transfers[p.name]["count"] += 1
            transfers[p.name]["jobs"].append(str(step.job.pk))

    for p in transfers:
        x = {"processName": p}
        x.update(transfers[p])
        x["jobs"] = ",".join(x["jobs"])
        processData.append(x)

    return render(request, 'partial/waiting_reports_table.html', {"processes": processData})


def waitingCount(_request):
    value = Job.objects.filter(
        Q(status=Status.AWAITING_HUMAN_VALIDATION) | Q(status=Status.AWAITING_HUMAN_INPUT)).count()
    if value == 0:
        return HttpResponse("")
    else:
        return HttpResponse(str(value))


def bulkEditJobs(request, step: str, jobs: str):
    if step == "fac_manual":
        context = bulkFacManual(request, jobs)
        if context:
            return render(request, "partial/bulk_edit_job.html", context)
        else:
            return HttpResponseRedirect(reverse('metadata:waiting_jobs'))
    else:
        return HttpResponseRedirect(reverse('metadata:waiting_jobs'))
