from datetime import datetime
from io import BytesIO
from typing import Dict, Any

from django.conf import settings
from django.http import HttpResponseRedirect, FileResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import View

from metadata.models import ExtractionTransfer, Job, Status, ProcessingStep
from metadata.pipeline_views.arab import arabGenerate, arabManual, arabMint, arabFilename, arabTranslate
from metadata.pipeline_views.fac import mint, facManual, facFilename, facTranslate
from metadata.pipeline_views.shared import ner, compute, filemaker
from metadata.utils import buildTransferCsvs, buildStructMap, buildFolderStructure


def index(request):
    return render(request, "partial/index_partial.html", {})


def waitingJobs(request):
    return render(request, "partial/waiting_partial.html", {})


def jobDetails(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    stepData = []
    for step in job.processingSteps.order_by("order"):
        urlName = step.processingStepType.lower()

        if urlName == "filename":
            urlName = f"{settings.ARCHIVE_INST.lower()}_{urlName}"
        stepData.append({"step": step, "urlName": urlName})

    error = {}
    if job.status == Status.ERROR:
        step = job.processingSteps.filter(status=Status.ERROR).first()
        error["message"] = step.log
        error["step"] = ProcessingStep.ProcessingStepType[step.processingStepType].label
    return render(request, "partial/job.html", {"job": job, "error": error, "steps": stepData})


def downloadTransfer(_request, transfer_id: int, filetype: str):
    transfer = get_object_or_404(ExtractionTransfer, pk=transfer_id)
    forArab = settings.ARCHIVE_INST == "ARAB"

    if filetype == "csv":
        outFile = buildTransferCsvs(transfer, forArab=forArab)
        return FileResponse(outFile, as_attachment=True,
                            filename=f"Omeka_CSVs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip")
    elif filetype == "csv_restricted":
        outFile = buildTransferCsvs(transfer, checkRestriction=True, forArab=forArab)
        return FileResponse(outFile, as_attachment=True,
                            filename=f"restricted_Omeka_CSVs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip")
    elif filetype == "struct_map":
        outFile = buildStructMap(transfer)
        return FileResponse(BytesIO(outFile.encode()), as_attachment=True, filename="mets_structmap.xml")
    elif filetype == "zip_restricted":
        outFile = buildFolderStructure(transfer, checkRestriction=True, forArab=forArab)
        folderName = transfer.name.replace(" ", "_")
        return FileResponse(outFile, as_attachment=True,
                            filename=f"restricted_{folderName}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip")
    elif filetype == "zip":
        outFile = buildFolderStructure(transfer, forArab=forArab)
        folderName = transfer.name.replace(" ", "_")
        return FileResponse(outFile, as_attachment=True,
                            filename=f"{folderName}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip")
    else:
        # TODO: raise error
        pass


class Transfers(View):

    def get(self, request, *_args, **_kwargs):
        INV = "lightgray"
        VIS = "black"
        sortInstruction = request.GET.get("sort", "updated:asc").split(":")
        viewStatus = {"name": {"up": INV, "down": INV, "sortUrl": "sort=name:asc"},
                      "status": {"up": INV, "down": INV, "sortUrl": "sort=status:asc"},
                      # "created": {"up": INV, "down": INV, "sortUrl": "sort=created:asc"},
                      "updated": {"up": INV, "down": INV, "sortUrl": "sort=updated:asc"}
                      }
        if len(sortInstruction) != 2:
            orderBy = "lastUpdated"
            viewKey = "updated"
        else:
            lookup = {"name": "name", "status": "status", "updated": "lastUpdated"}
            if sortInstruction[0] in lookup:
                viewKey = sortInstruction[0]
                orderBy = lookup[sortInstruction[0]]
            else:
                viewKey = "updated"
                orderBy = "lastUpdated"
        if len(sortInstruction) < 2 or sortInstruction[1] == "desc":
            viewStatus[viewKey]["down"] = VIS
            viewStatus[viewKey]["sortUrl"] = f"sort={viewKey}:asc"
            context = {"jobs": ExtractionTransfer.objects.order_by(orderBy).reverse(), "viewStatus": viewStatus,
                       "searchParams": f"sort={viewKey}:desc", "archive": settings.ARCHIVE_INST}
        else:
            viewStatus[viewKey]["up"] = VIS
            viewStatus[viewKey]["sortUrl"] = f"sort={viewKey}:desc"
            context = {"jobs": ExtractionTransfer.objects.order_by(orderBy), "viewStatus": viewStatus,
                       "searchParams": f"sort={viewKey}:asc", "archive": settings.ARCHIVE_INST}

        return render(request, "partial/extraction_transfer_table.html", context)

    def delete(self, request, *_args, **_kwargs):
        transfers = ExtractionTransfer.objects.filter(id__in=[int(id) for id in request.GET.getlist("ids")])
        for transfer in transfers:
            transfer.delete()
        return HttpResponse(status=204, headers={"HX-Trigger": "collection-deleted"})


class Transfer(View):
    def get(self, request, *_args, **kwargs):
        if "transfer_id" in kwargs:
            transferId = kwargs["transfer_id"]
            transfer = get_object_or_404(ExtractionTransfer, pk=transferId)
            # if job:
            #     pages = Page.objects.filter(job=transferId)
            #     metadata = loadMetadata(job.metadata)
            return render(request, "modal/transfer_detail.html", {"transfer": transfer})
        else:
            return HttpResponseRedirect("/")

    def delete(self, request, *_args, **kwargs):
        transfer = get_object_or_404(ExtractionTransfer, pk=kwargs["transfer_id"])
        transfer.delete()
        if request.GET.get("redirect", False) is not None:
            return HttpResponse(status=204, headers={"HX-Redirect": "/"})
        else:
            return HttpResponse(status=204, headers={"HX-Trigger": "collection-deleted"})


class JobEditView(View):
    def get(self, request, *_args, **kwargs):
        job = get_object_or_404(Job, pk=kwargs["job_id"])
        stepName = kwargs["step"]
        context = self.handleView(request, job, stepName)
        return render(request, "partial/edit_job.html", context)

    def post(self, request, *_args, **kwargs):
        job = get_object_or_404(Job, pk=kwargs["job_id"])

        if request.POST['confirm'] == 'Confirm':  # TODO: add cancel button :D
            stepName = kwargs["step"]
            context = self.handleView(request, job, stepName)  # TODO: do we need to return anything here?
            # TODO: only if there are errors, in which case it should be the same as GET + error context ...
            if "form" in context:
                return render(request, "partial/edit_job.html", context)
            else:
                return HttpResponseRedirect(reverse('metadata:job', kwargs={'job_id': kwargs["job_id"]}))
        else:
            return HttpResponseRedirect(reverse('metadata:job', kwargs={'job_id': kwargs["job_id"]}))

    def handleView(self, request, job, stepName) -> Dict[str, Any]:
        stepIndex = {"fac_filename": facFilename, "arab_filename": arabFilename, "filemaker_lookup": filemaker,
                     "generate": compute, "fac_manual": facManual, "ner": ner, "mint_arks": mint,
                     "arab_generate": arabGenerate, "arab_manual": arabManual, "arab_mint_handle": arabMint,
                     "arab_translate_to_swedish": arabTranslate, "fac_translate_to_swedish": facTranslate}
        context = stepIndex[stepName](request, job)
        context["stepParam"] = stepName
        return context
