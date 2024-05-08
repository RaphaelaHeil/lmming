from datetime import date

from django.http import QueryDict
from django.shortcuts import render, get_object_or_404, redirect

from metadata.enum_utils import PipelineStepName
from metadata.forms import ExtractionTransferDetailForm, ExtractionTransferSettingsForm, SettingsForm
from metadata.models import ExtractionTransfer, Report, Page, Status, Job, ProcessingStep, DefaultValueSettings, \
    DefaultNumberSettings, UrlSettings
from metadata.utils import parseFilename, buildReportIdentifier


def downloadTransfer():
    pass

def donwloadModal():
    pass


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
    iiifUrl = UrlSettings.objects.filter(pk=UrlSettings.UrlSettingsType.IIIF).first()
    atomUrl = UrlSettings.objects.filter(pk=UrlSettings.UrlSettingsType.ATOM).first()
    language = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE).first()
    license = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE).first()
    source = DefaultValueSettings.objects.filter(pk=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE).first()
    accessRights = DefaultValueSettings.objects.filter(
        pk=DefaultValueSettings.DefaultValueSettingsType.DC_ACCESS_RIGHTS).first()
    avilableYearOffset = DefaultNumberSettings.objects.filter(
        pk=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET).first()
    initial = {"iiifURL": iiifUrl.url if iiifUrl else "",
               "atomURL": atomUrl.url if atomUrl else "",
               "language": language.value if language else "",
               "license": license.value if license else "",
               "source": source.value if source else "",
               "accessRights": accessRights.value if accessRights else "",
               "avilableYearOffset": avilableYearOffset.value if avilableYearOffset else 0
               }
    if request.method == 'POST':
        settingsForm = SettingsForm(request.POST, initial=initial)
        if settingsForm.is_valid():
            if settingsForm.has_changed():
                if "iiifURL" in settingsForm.changed_data:
                    if iiifUrl:
                        iiifUrl.value = settingsForm.cleaned_data["iiifURL"]
                        iiifUrl.save()
                    else:
                        UrlSettings.objects.create(pk=UrlSettings.UrlSettingsType.IIIF,
                                                   value=settingsForm.cleaned_data["iiifURL"])
                if "atomUrl" in settingsForm.changed_data:
                    if atomUrl:
                        atomUrl.value = settingsForm.cleaned_data["atomUrl"]
                        atomUrl.save()
                    else:
                        UrlSettings.objects.create(pk=UrlSettings.UrlSettingsType.ATOM,
                                                   value=settingsForm.cleaned_data["atomUrl"])
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
                        source.value()
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
        else:
            pass  # TODO: return error or smth
        return redirect("/")
    else:
        return render(request, 'modal/settings.html', {"form": SettingsForm(initial=initial)})


def verifyTransfer(request, transfer_id):
    transferInstance = get_object_or_404(ExtractionTransfer, pk=transfer_id)

    if request.method == "POST":
        transferInstance.status = Status.PENDING
        transferInstance.save()
        # TODO: add delete button,
        return redirect("/")

    return render(request, "partial/verify_transfer.html", {"transfer": transferInstance})


def __buildProcessingSteps__(data, job):
    steps = []
    stepKeys = [("filenameMode", "filenameHumVal", PipelineStepName.FILENAME),
                ("filemakerMode", "filemakerHumVal", PipelineStepName.FILEMAKER_LOOKUP),
                ("generateMode", "generateHumVal", PipelineStepName.GENERATE),
                ("imageMode", "imageHumVal", PipelineStepName.IMAGE),
                ("nerMode", "nerHumVal", PipelineStepName.NER),
                ("mintMode", "mintHumVal", PipelineStepName.MINT_ARKS)]

    for mode, humVal, stepName in stepKeys:
        p = ProcessingStep.objects.create(job=job, order=stepName.value[0], processingStepType=stepName,
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
                    Page.objects.create(report=r, order=int(page["page"]), transcriptionFile=page["file"])

                j = Job.objects.create(transfer=transferInstance, report=r)
                if not processingSteps:
                    processingSteps = __buildProcessingSteps__(extractionSettingsForm.cleaned_data, j)
                else:
                    for step in processingSteps:
                        step.pk = None
                        step._state.adding = True
                        step.job = j
                        step.save()
                r.job = j  # do I need a save after this?
                r.save()

            return redirect("metadata:verify_transfer", transfer_id=transferInstance.pk)

    return render(request, 'partial/create_transfer.html',
                  {"detailform": detailform, "settings": extractionSettingsForm})
