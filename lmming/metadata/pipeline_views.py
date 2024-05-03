import datetime
from datetime import date
from typing import List, Any

from django.http import QueryDict
from django.shortcuts import render, get_object_or_404, redirect

from metadata.enum_utils import PipelineStepName
from metadata.forms import ExtractionTransferDetailForm, ExtractionTransferSettingsForm, FileNameForm, FilemakerForm, \
    ComputeForm, ImageForm
from metadata.models import ExtractionTransfer, Report, Page, Status, Job, ProcessingStep
from metadata.utils import parseFilename, buildReportIdentifier
from django.forms import formset_factory


def __toDisplayList__(input: List[Any]) -> str:
    if input:
        return ", ".join([str(i) for i in input])
    else:
        return ""


def __fromDisplayList__(input: str) -> List[Any]:
    if input:
        return [s.strip() for s in input.split(",")]
    else:
        return []


def filename(request, job):
    # add a check that the user is allowed to see/modify this view? otherwise return general job view?
    if request.method == "POST":
        filenameForm = FileNameForm(request.POST,
                                    initial={"organisationID": job.report.unionId, "type": job.report.type,
                                             "date": __toDisplayList__(job.report.date)})
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
            else:
                # TODO: update processing status and trigger next one
                pass
            return "partial/job.html", {"job": job}
        else:
            return "partial/job.html", {"job": job}
    else:
        filenameForm = FileNameForm(initial={"organisationID": job.report.unionId, "type": job.report.type,
                                             "date": __toDisplayList__(job.report.date)})
        return 'partial/filename_result.html', {"form": filenameForm, "job": job}


def filemaker(request, job):
    initial = {"creator": job.report.creator, "relation": __toDisplayList__(job.report.relation),
               "coverage": job.report.coverage, "spatial": __toDisplayList__(job.report.spatial)}
    if request.method == "POST":
        filemakerForm = FilemakerForm(request.POST, initial=initial)
        if filemakerForm.is_valid():
            if filemakerForm.has_changed():
                if "creator" in filemakerForm.changed_data:
                    job.report.creator = filemakerForm.cleaned_data["creator"]
                if "relation" in filemakerForm.changed_data:
                    job.report.relation = __fromDisplayList__(filemakerForm.cleaned_data["relation"])
                if "coverage" in filemakerForm.changed_data:
                    job.report.coverage = filemakerForm.cleaned_data["coverage"]
                if "spatial" in filemakerForm.changed_data:
                    job.report.spatial = __fromDisplayList__(filemakerForm.cleaned_data["spatial"])
                job.report.save()
            else:
                pass  # mark filemaker step as complete and trigger next one
        return "partial/job.html", {"job": job}
    else:
        filemakerForm = FilemakerForm(initial=initial)
        return "partial/filemaker_result.html", {"form": filemakerForm, "job": job}


def compute(request, job):
    initial = {"title": job.report.title, "created": job.report.created.year if job.report.created else "",
               "available": job.report.available, "description": job.report.description,
               "language": __toDisplayList__(job.report.language), "license": __toDisplayList__(job.report.license),
               "source": __toDisplayList__(job.report.source), "accessRights": job.report.accessRights}
    if request.method == "POST":
        computeForm = ComputeForm(request.POST, initial=initial)
        if computeForm.is_valid():
            if computeForm.has_changed():
                if "title" in computeForm.changed_data:
                    job.report.title = computeForm.cleaned_data["title"]
                if "created" in computeForm.changed_data:
                    job.report.created = date(int(computeForm.cleaned_data["created"]), month=1, day=1)
                if "available" in computeForm.changed_data:
                    job.report.available = computeForm.cleaned_data["available"]
                if "description" in computeForm.changed_data:
                    job.report.description = computeForm.cleaned_data["description"]
                if "language" in computeForm.changed_data:
                    job.report.language = __fromDisplayList__(computeForm.cleaned_data["language"])
                if "license" in computeForm.changed_data:
                    job.report.license = __fromDisplayList__(computeForm.cleaned_data["license"])
                if "source" in computeForm.changed_data:
                    job.report.source = __fromDisplayList__(computeForm.cleaned_data["source"])
                if "accessRights" in computeForm.changed_data:
                    job.report.accessRights = computeForm.cleaned_data["accessRights"]
                job.report.save()
            else:
                pass  # make step as complte and trigger next one
        return "partial/job.html", {"job": job}
    else:
        computeForm = ComputeForm(initial=initial)
        return "partial/compute_result.html", {"form": computeForm, "job": job}


def imageBased(request, job):
    initial = {"isFormatOf":job.report.isFormatOf}
    if request.method == "POST":
        imageForm = ImageForm(request.POST, initial=initial)
        if imageForm.is_valid():
            if imageForm.has_changed():
                if "isFormatOf" in imageForm.changed_data:
                    job.report.isFormatOf = imageForm.cleaned_data["isFormatOf"]
                job.report.save()
            else:
                pass
        return "partial/job.html", {"job": job}
    else:
        imageForm = ImageForm(initial=initial)
        return "partial/image_result.html", {"form":imageForm, "job": job}


def ner(request, job):
    if request.method == "POST":
        return "partial/job.html", {"job": job}
    else:
        return "partial/job.html", {"job": job}


def mint(request, job):
    if request.method == "POST":
        return "partial/job.html", {"job": job}
    else:
        return "partial/job.html", {"job": job}
