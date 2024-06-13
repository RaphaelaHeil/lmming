from datetime import datetime
from typing import Tuple, Dict, Any

from django.http import HttpResponseRedirect, FileResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import View

from metadata.lookup import URL_STEP_INDEX
from metadata.models import ExtractionTransfer, Job, Status, ProcessingStep
from metadata.pipeline_views import filename, filemaker, compute, facManual, ner, mint
from metadata.utils import buildTransferCsvs


def index(request):
    return render(request, "partial/index_partial.html", {})


def waitingJobs(request):
    return render(request, "partial/waiting_partial.html", {})


def jobDetails(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    stepData = []
    for step in job.processingSteps.order_by("order"):
        stepData.append({"step": step, "urlName": URL_STEP_INDEX[step.processingStepType]})

    error = {}
    if job.status == Status.ERROR:
        step = job.processingSteps.filter(status=Status.ERROR).first()
        error["message"] = step.log
        error["step"] = ProcessingStep.ProcessingStepType[step.processingStepType].label
    return render(request, "partial/job.html", {"job": job, "error": error, "steps":stepData})


def downloadTransfer(request, transfer_id):
    # TODO: add a check if transfer is complete!
    transfer = get_object_or_404(ExtractionTransfer, pk=transfer_id)

    if transfer:
        outFile = buildTransferCsvs(transfer)
        return FileResponse(outFile, as_attachment=True,
                            filename=f"Omeka_CSVs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.zip")


class Transfers(View):

    def get(self, request, *args, **kwargs):
        INV = "lightgray"
        VIS = "black"
        sortInstruction = request.GET.get("sort", "created:asc").split(":")
        viewStatus = {"name": {"up": INV, "down": INV, "sortUrl": "sort=name:asc"},
                      "status": {"up": INV, "down": INV, "sortUrl": "sort=status:asc"},
                      "created": {"up": INV, "down": INV, "sortUrl": "sort=created:asc"}}
        if len(sortInstruction) != 2:
            orderBy = "dateCreated"
            viewKey = "created"
        else:
            lookup = {"name": "name", "status": "status", "created": "dateCreated", "started": "startDate",
                      "ended": "endDate"}
            if sortInstruction[0] in lookup:
                viewKey = sortInstruction[0]
                orderBy = lookup[sortInstruction[0]]
            else:
                viewKey = "created"
                orderBy = "dateCreated"
        if len(sortInstruction) < 2 or sortInstruction[1] == "desc":
            viewStatus[viewKey]["down"] = VIS
            viewStatus[viewKey]["sortUrl"] = f"sort={viewKey}:asc"
            context = {"jobs": ExtractionTransfer.objects.order_by(orderBy).reverse(), "viewStatus": viewStatus,
                       "searchParams": f"sort={viewKey}:desc"}
        else:
            viewStatus[viewKey]["up"] = VIS
            viewStatus[viewKey]["sortUrl"] = f"sort={viewKey}:desc"
            context = {"jobs": ExtractionTransfer.objects.order_by(orderBy), "viewStatus": viewStatus,
                       "searchParams": f"sort={viewKey}:asc"}

        # return render(request, "partial/extraction_transfer_table.html", context)

        return render(request, "partial/extraction_transfer_table.html", context)

    def delete(self, request, *args, **kwargs):
        transfers = ExtractionTransfer.objects.filter(id__in=[int(id) for id in request.GET.getlist("ids")])
        for transfer in transfers:
            transfer.delete()
        return HttpResponse(status=204, headers={"HX-Trigger": "collection-deleted"})


class Transfer(View):
    def get(self, request, *args, **kwargs):
        if "transfer_id" in kwargs:
            transferId = kwargs["transfer_id"]
            transfer = get_object_or_404(ExtractionTransfer, pk=transferId)
            # if job:
            #     pages = Page.objects.filter(job=transferId)
            #     metadata = loadMetadata(job.metadata)
            return render(request, "modal/transfer_detail.html", {"transfer": transfer})
        else:
            return HttpResponseRedirect("/")

    def delete(self, request, *args, **kwargs):
        transfer = get_object_or_404(ExtractionTransfer, pk=kwargs["transfer_id"])
        transfer.delete()
        return HttpResponse(status=204, headers={"HX-Trigger": "collection-deleted"})


class JobEditView(View):
    def get(self, request, *args, **kwargs):
        job = get_object_or_404(Job, pk=kwargs["job_id"])
        stepName = kwargs["step"]
        context = self.__handleView__(request, job, stepName)
        return render(request, "partial/edit_job.html", context)

    def post(self, request, *args, **kwargs):
        job = get_object_or_404(Job, pk=kwargs["job_id"])

        if request.POST['confirm'] == 'Confirm':  # TODO: add cancel button :D
            stepName = kwargs["step"]
            context = self.__handleView__(request, job, stepName)  # TODO: do we need to return anything here?
            # TODO: only if there are errors, in which case it should be the same as GET + error context ...
            return HttpResponseRedirect(reverse('metadata:job', kwargs={'job_id': kwargs["job_id"]}))
        else:
            return HttpResponseRedirect(reverse('metadata:job', kwargs={'job_id': kwargs["job_id"]}))

    def __handleView__(self, request, job, stepName) -> Tuple[str, Dict[str, Any]]:
        stepIndex = {"filename": filename, "filemaker": filemaker, "generate": compute, "image": facManual, "ner": ner,
                     "mint": mint}
        context = stepIndex[stepName](request, job)
        context["stepParam"] = stepName
        return context
