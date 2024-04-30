import datetime
from datetime import date

from django.http import QueryDict
from django.shortcuts import render, get_object_or_404, redirect

from metadata.enum_utils import PipelineStepName
from metadata.forms import ExtractionTransferDetailForm, ExtractionTransferSettingsForm, FileNameForm
from metadata.models import ExtractionTransfer, Report, Page, Status, Job, ProcessingStep
from metadata.utils import parseFilename, buildReportIdentifier
from django.forms import formset_factory


def filename(request, job):
    # add a check that the user is allowed to see/modify this view? otherwise return general job view?
    if request.method == "POST":
        filenameForm = FileNameForm(request.POST,
                                    initial={"organisationID": job.report.unionId, "type": job.report.type,
                                             "date": ", ".join([str(d.year) for d in job.report.date])})
        if filenameForm.is_valid() and filenameForm.has_changed():
            # print(filenameForm.cleaned_data)
            # {'organisationID': '1111', 'type': ['ANNUAL_REPORT', 'FINANCIAL_STATEMENT'], 'date': '1999'}
            if "organisationID" in filenameForm.changed_data:
                job.report.unionId = filenameForm.cleaned_data["organisationID"]
            if "type" in filenameForm.changed_data:
                job.report.type = filenameForm.cleaned_data["type"]
            if "date" in filenameForm.changed_data:
                years = [int(d.strip()) for d in filenameForm.data["date"].split(",")]
                job.report.date = [datetime.date(year=y, month=1, day=1) for y in years]
            job.report.save()
            # TODO: update processing status and trigger next one
            # TODO: return general job view
            return "partial/job.html", {"job": job}
        else:
            # TODO: update processind step state and trigger next one
            # TODO: return general job view
            return "partial/job.html", {"job": job}
    else:
        # get job, get report for job, collect result to populate the form
        filenameForm = FileNameForm(initial={"organisationID": job.report.unionId, "type": job.report.type,
                                             "date": ", ".join([str(d.year) for d in job.report.date])})
        return 'partial/filename_result.html', {"form": filenameForm, "job": job}


def filemaker():
    pass


def compute():
    pass


def imageBased():
    pass


def ner():
    pass


def mint():
    pass
