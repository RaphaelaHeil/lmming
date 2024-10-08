from datetime import date

from django.db import transaction
from django.forms import formset_factory

from metadata.forms.fac import ComputeForm
from metadata.forms.shared import FilemakerForm, PageForm
from metadata.models import Page, Status, ProcessingStep
from metadata.pipeline_views.utils import __fromDisplayList__, __toDisplayList__
from metadata.tasks.manage import scheduleTask


def filemaker(request, job):
    initial = {"creator": job.report.creator, "relation": job.report.get_relation_display(),
               "coverage": job.report.coverage, "spatial": job.report.get_spatial_display(),
               "isVersionOf": job.report.isVersionOf}
    if request.method == "POST":
        filemakerForm = FilemakerForm(request.POST, initial=initial)
        if filemakerForm.is_valid():
            if filemakerForm.has_changed():
                if "creator" in filemakerForm.changed_data:
                    job.report.creator = filemakerForm.cleaned_data["creator"]
                if "relation" in filemakerForm.changed_data:
                    job.report.relation = __fromDisplayList__(filemakerForm.cleaned_data["relation"])
                if "isVersionOf" in filemakerForm.changed_data:
                    job.report.relation = __fromDisplayList__(filemakerForm.cleaned_data["isVersionOf"])
                if "coverage" in filemakerForm.changed_data:
                    job.report.coverage = filemakerForm.cleaned_data["coverage"]
                if "spatial" in filemakerForm.changed_data:
                    job.report.spatial = __fromDisplayList__(filemakerForm.cleaned_data["spatial"])
                job.report.save()
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": filemakerForm, "job": job,
                    "stepName": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.label}
    else:
        filemakerForm = FilemakerForm(initial=initial)
        return {"form": filemakerForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.label}


def compute(request, job):
    initial = {"title": job.report.title, "created": job.report.created.year if job.report.created else "",
               "available": job.report.available, "description": job.report.description,
               "language": job.report.get_language_display(), "license": job.report.get_license_display(),
               "source": job.report.get_source_display(), "accessRights": job.report.accessRights}
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
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": computeForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.GENERATE.label}
    else:
        computeForm = ComputeForm(initial=initial)
        return {"form": computeForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.GENERATE.label}


def ner(request, job):
    NerFormSet = formset_factory(PageForm, extra=0)
    initial = [{"measures": p.measures, "transcription": p.transcription,
                "normalisedTranscription": p.normalisedTranscription,
                "persons": __toDisplayList__(p.persons),
                "organisations": __toDisplayList__(p.organisations),
                "locations": __toDisplayList__(p.locations),
                "times": __toDisplayList__(p.times),
                "works": __toDisplayList__(p.works),
                "events": __toDisplayList__(p.events),
                "ner_objects": __toDisplayList__(p.ner_objects),
                "pageId": p.pk, "order": p.order} for p in job.report.page_set.all().order_by("order")]

    if request.method == "POST":
        nerForm = NerFormSet(request.POST, initial=initial)
        if nerForm.is_valid():
            for f in nerForm:
                if f.has_changed():
                    page = Page.objects.get(pk=f.pageId)
                    if "measures" in f.changed_data:
                        page.measures = f.cleaned_data["measures"]
                    if "transcription" in f.changed_data:
                        page.transcription = f.cleaned_data["transcription"]
                    if "normalisedTranscription" in f.changed_data:
                        page.normalisedTranscription = f.cleaned_data["normalisedTranscription"]
                    if "persons" in f.changed_data:
                        page.persons = __fromDisplayList__(f.cleaned_data["persons"])
                    if "organisations" in f.changed_data:
                        page.organisations = __fromDisplayList__(f.cleaned_data["organisations"])
                    if "locations" in f.changed_data:
                        page.locations = __fromDisplayList__(f.cleaned_data["locations"])
                    if "times" in f.changed_data:
                        page.times = __fromDisplayList__(f.cleaned_data["times"])
                    if "works" in f.changed_data:
                        page.works = __fromDisplayList__(f.cleaned_data["works"])
                    if "events" in f.changed_data:
                        page.events = __fromDisplayList__(f.cleaned_data["events"])
                    if "ner_objects" in f.changed_data:
                        page.ner_objects = __fromDisplayList__(f.cleaned_data["ner_objects"])
                    page.save()
            step = job.processingSteps.filter(processingStepType=ProcessingStep.ProcessingStepType.NER.value).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            return {"form": nerForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.NER.label}
    else:
        nerForm = NerFormSet(initial=initial)
        return {"form": nerForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.NER.label}
