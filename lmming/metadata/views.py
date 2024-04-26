from django.shortcuts import render
import zipfile
from datetime import datetime
from io import BytesIO

from django.http import HttpResponseRedirect, FileResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import View
from django.utils.crypto import get_random_string

from metadata.models import ExtractionTransfer


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
        pass
