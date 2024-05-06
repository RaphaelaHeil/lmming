from django.shortcuts import render
import zipfile
from datetime import datetime
from io import BytesIO

from django.http import HttpResponseRedirect, FileResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View
from django.utils.crypto import get_random_string

from metadata.models import ExtractionTransfer, Job, Status, ProcessingStep
from metadata.pipeline_views import filename, filemaker, compute, imageBased, ner, mint


def index(request):
    return render(request, "partial/index_partial.html", {})


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


class JobView(View):

    def get(self, request, *args, **kwargs):
        templateName, context = self.__handleStepRedirect__(request, args, kwargs)
        return render(request, templateName, context)

    def post(self, request, *args, **kwargs):
        if request.POST['submit'] == 'confirm':
            templateName, context = self.__handleStepRedirect__(request, args, kwargs)
            return render(request, templateName, context)
        else:
            job = get_object_or_404(Job, pk=kwargs["job_id"])
            return "partial/job.html", {"job": job}

    def __handleStepRedirect__(self, request, args, kwargs):
        job = get_object_or_404(Job, pk=kwargs["job_id"])

        if job.status in [Status.AWAITING_HUMAN_INPUT, Status.AWAITING_HUMAN_VALIDATION]:
            for step in job.processingSteps.order_by("order"):
                if step.status in [Status.AWAITING_HUMAN_VALIDATION, Status.AWAITING_HUMAN_VALIDATION]:
                    match step.processingStepType:
                        case ProcessingStep.ProcessingStepType.FILENAME:
                            return filename(request, job)
                        case ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP:
                            return filemaker(request, job)
                        case ProcessingStep.ProcessingStepType.GENERATE:
                            return compute(request, job)
                        case ProcessingStep.ProcessingStepType.IMAGE:
                            return imageBased(request, job)
                        case ProcessingStep.ProcessingStepType.NER:
                            return ner(request, job)
                        case ProcessingStep.ProcessingStepType.MINT_ARKS:
                            return mint(request, job)
                        case _:
                            # TODO: add loggin
                            return "partial/job.html", {"job": job}
        else:
            return "partial/job.html", {"job": job}
