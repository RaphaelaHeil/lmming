import datetime
from datetime import date
from typing import List, Any

from django.db import transaction
from django.forms import formset_factory

from metadata.forms import FileNameForm, FilemakerForm, ComputeForm, ImageForm, MintForm, PageForm
from metadata.models import Page, Status, ProcessingStep
from metadata.tasks import scheduleTask


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
        filenameForm = FileNameForm(request.POST, initial={"organisationID": job.report.unionId,
                                                           "type": job.report.type,
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

            step = job.processingSteps.filter(processingStepType=ProcessingStep.ProcessingStepType.FILENAME).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}  # TODO: double-check this return type ...
        else:
            # TODO: return errors!
            return {"job": job}
    else:
        filenameForm = FileNameForm(initial={"organisationID": job.report.unionId, "type": job.report.type,
                                             "date": __toDisplayList__(job.report.date)})
        return {"form": filenameForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILENAME.label}


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
            step = job.processingSteps.filter(
                processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            # TODO: return errors?!
            return {"job": job}
    else:
        filemakerForm = FilemakerForm(initial=initial)
        return {"form": filemakerForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.label}


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
            step = job.processingSteps.filter(processingStepType=ProcessingStep.ProcessingStepType.GENERATE).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            # TODO: return errors?!
            return {"job": job}
    else:
        computeForm = ComputeForm(initial=initial)
        return {"form": computeForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.GENERATE.label}


def imageBased(request, job):
    initial = {"isFormatOf": job.report.isFormatOf}
    if request.method == "POST":
        imageForm = ImageForm(request.POST, initial=initial)
        if imageForm.is_valid():
            if imageForm.has_changed():
                if "isFormatOf" in imageForm.changed_data:
                    job.report.isFormatOf = imageForm.cleaned_data["isFormatOf"]
                job.report.save()
            step = job.processingSteps.filter(processingStepType=ProcessingStep.ProcessingStepType.IMAGE).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            # TODO: return errors
            return {"job": job}
    else:
        imageForm = ImageForm(initial=initial)
        return {"form": imageForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.IMAGE.label}


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
            step = job.processingSteps.filter(processingStepType=ProcessingStep.ProcessingStepType.NER).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            # TODO: return errors?!
            return {"job": job}
    else:
        nerForm = NerFormSet(initial=initial)
        return {"form": nerForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.NER.label}


def mint(request, job):
    initial = {"identifier": job.report.identifier, "isVersionOf": job.report.identifier}
    if request.method == "POST":
        mintForm = MintForm(request.POST, initial=initial)
        if mintForm.is_valid():
            if mintForm.has_changed():
                if "identifier" in mintForm.changed_data:
                    job.report.identifier = mintForm.cleaned_data["identifier"]
                if "isVersionOf" in mintForm.changed_data:
                    job.report.isVersionOf = mintForm.cleaned_data["isVersionOf"]
                job.report.save()
            step = job.processingSteps.filter(processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS).first()
            step.status = Status.COMPLETE
            step.save()
            transaction.on_commit(lambda: scheduleTask(job.pk))
            return {"job": job}
        else:
            # TODO: return errors?!
            return {"job": job}
    else:
        mintForm = MintForm(initial=initial)
        return {"form": mintForm, "job": job, "stepName": ProcessingStep.ProcessingStepType.MINT_ARKS.label}
