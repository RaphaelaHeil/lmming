from django.forms import formset_factory
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views.generic import View

from v2.forms.project import ProjectForm
from v2.forms.vocabulary import VocabularyForm, MetadataTermForm
from v2.models import Vocabulary, MetadataTerm, Project, Process


def index(request):
    return render(request, "v2/partial/index_partial.html", {})


class ProcessesView(View):

    def get(self, request, *_args, **_kwargs):
        INV = "lightgray"
        VIS = "black"
        sortInstruction = request.GET.get("sort", "updated:desc").split(":")
        viewStatus = {"name": {"up": INV, "down": INV, "sortUrl": "sort=name:asc"},
                      "abbreviation": {"up": INV, "down": INV, "sortUrl": "sort=abbreviation:asc"},
                      "status": {"up": INV, "down": INV, "sortUrl": "sort=status:asc"},
                      # "created": {"up": INV, "down": INV, "sortUrl": "sort=created:asc"},
                      "updated": {"up": INV, "down": INV, "sortUrl": "sort=updated:asc"}
                      }
        if len(sortInstruction) != 2:
            orderBy = "lastModified"
            viewKey = "updated"
        else:
            lookup = {"name": "name", "status": "status", "updated": "lastModified",
                      "abbreviation": "project__abbreviation"}
            if sortInstruction[0] in lookup:
                viewKey = sortInstruction[0]
                orderBy = lookup[sortInstruction[0]]
            else:
                viewKey = "updated"
                orderBy = "lastModified"

        if len(sortInstruction) < 2 or sortInstruction[1] == "desc":
            viewStatus[viewKey]["down"] = VIS
            viewStatus[viewKey]["sortUrl"] = f"sort={viewKey}:asc"
            context = {"processes": Process.objects.order_by(orderBy).reverse(), "viewStatus": viewStatus,
                       "searchParams": f"sort={viewKey}:desc"}
        else:
            viewStatus[viewKey]["up"] = VIS
            viewStatus[viewKey]["sortUrl"] = f"sort={viewKey}:desc"
            context = {"processes": Process.objects.order_by(orderBy), "viewStatus": viewStatus,
                       "searchParams": f"sort={viewKey}:asc"}

        return render(request, "v2/partial/process/table.html", context)

    def delete(self, request, *_args, **_kwargs):
        processes = Process.objects.filter(id__in=[int(id) for id in request.GET.getlist("ids")])
        for process in processes:
            process.delete()
        return HttpResponse(status=204, headers={"HX-Trigger": "collection-deleted"})


class ProcessView(View):
    def get(self, request, *_args, **kwargs):
        if "process_id" in kwargs:
            process = get_object_or_404(Process, pk=kwargs["process_id"])
            return render(request, "v2/partial/process/details.html", {"process": process})
        else:
            return HttpResponseRedirect("/")

    def delete(self, request, *_args, **kwargs):
        process = get_object_or_404(Process, pk=kwargs["process_id"])
        process.delete()
        if request.GET.get("redirect", False) is not None:
            return HttpResponse(status=204, headers={"HX-Redirect": "/v2"})
        else:
            return HttpResponse(status=204, headers={"HX-Trigger": "collection-deleted"})


class VocabularyView(View):

    def get(self, request, *args, **kwargs):
        mode = request.GET.get("mode", "view")
        if mode == "create":
            form = VocabularyForm(initial={})
            MetadataFormSet = formset_factory(MetadataTermForm, extra=0)
            metadataForm = MetadataFormSet(initial={})

            return render(request, "v2/partial/vocabulary/create_edit.html",
                          context={"form": form, "mode": mode, "metadataForm": metadataForm})

        if "id" in kwargs:
            vocabulary = get_object_or_404(Vocabulary, pk=kwargs["id"])

            if mode == "edit":
                form = VocabularyForm(initial={"description": vocabulary.description, "name": vocabulary.name,
                                               "url": vocabulary.url})
                MetadataFormSet = formset_factory(MetadataTermForm, extra=0, can_delete=True)
                metadataForm = MetadataFormSet(
                    initial=[{"description": m.description, "standardTerm": m.standardTerm, "id": m.id} for m in
                             vocabulary.metadataterm_set.all()])
                return render(request, "v2/partial/vocabulary/create_edit.html",
                              context={"form": form, "id": vocabulary.pk, "mode": "edit", "metadataForm": metadataForm})
            else:
                return render(request, "v2/partial/vocabulary/details.html",
                              context={"vocabulary": vocabulary, "mode": mode})
        else:
            vocabularies = Vocabulary.objects.order_by("name")
            return render(request, "v2/partial/vocabulary/table.html", context={"vocabularies": vocabularies})

    def post(self, request, *args, **kwargs):
        mode = request.GET.get("mode", "view")

        MetadataFormSet = formset_factory(MetadataTermForm, can_delete=True)

        if mode == "edit":
            vocabulary = get_object_or_404(Vocabulary, pk=kwargs["id"])
            initial = {"description": vocabulary.description, "name": vocabulary.name, "url": vocabulary.url}
            metaDataInitial = [{"description": m.description, "standardTerm": m.standardTerm, "id": m.id} for m in
                               vocabulary.metadataterm_set.all()]
        else:
            vocabulary = Vocabulary()
            initial = {}
            metaDataInitial = {}
        vocabForm = VocabularyForm(request.POST, initial=initial)
        metadataForm = MetadataFormSet(request.POST, initial=metaDataInitial)

        if vocabForm.is_valid():
            if vocabForm.has_changed():
                if "name" in vocabForm.changed_data:
                    vocabulary.name = vocabForm.cleaned_data["name"]
                if "description" in vocabForm.changed_data:
                    vocabulary.description = vocabForm.cleaned_data["description"]
                if "url" in vocabForm.changed_data:
                    vocabulary.url = vocabForm.cleaned_data["url"]
        if metadataForm.is_valid():
            for f in metadataForm:
                if f.id < 0:
                    metadataTerm = MetadataTerm(vocabulary=vocabulary)
                else:
                    metadataTerm = vocabulary.metadataterm_set.get(pk=f.id)
                    if "DELETE" in f.cleaned_data and f.cleaned_data["DELETE"]:
                        metadataTerm.delete()
                        continue

                if "standardTerm" in f.cleaned_data:
                    metadataTerm.standardTerm = f.cleaned_data["standardTerm"]
                if "description" in f.cleaned_data:
                    metadataTerm.description = f.cleaned_data["description"]

                try:
                    metadataTerm.save()
                except:
                    metadataForm.error = "Standard terms have to be unique. Please rename any duplicates."
                    if mode == "create":
                        return render(request, "v2/partial/vocabulary/create_edit.html",
                                      context={"form": vocabForm, "mode": "create", "metadataForm": metadataForm})
                    else:
                        return render(request, "v2/partial/vocabulary/create_edit.html",
                                      context={"form": vocabForm, "id": vocabulary.pk, "mode": "edit",
                                               "metadataForm": metadataForm})
        vocabulary.save()
        return HttpResponseRedirect(reverse('v2:vocabularies'))


class ProjectView(View):

    def get(self, request, *args, **kwargs):
        mode = request.GET.get("mode", "view")
        if mode == "create":
            form = ProjectForm()

            return render(request, "v2/partial/project/create_edit.html", context={"form": form, "mode": mode})

        if "id" in kwargs:
            project = get_object_or_404(Project, pk=kwargs["id"])

            if mode == "edit":
                form = ProjectForm(initial={"name": project.name, "recordIdColumnName": project.recordIdColumnName,
                                            "description": project.description, "abbreviation": project.abbreviation,
                                            "externalRecordColumnNames": ",".join(project.externalRecordColumnNames)})
                # MetadataFormSet = formset_factory(MetadataTermForm, extra=0, can_delete=True)
                # metadataForm = MetadataFormSet(
                #     initial=[{"description": m.description, "standardTerm": m.standardTerm, "id": m.id} for m in
                #              vocabulary.metadataterm_set.all()])
                return render(request, "v2/partial/project/create_edit.html",
                              context={"form": form, "id": project.pk, "mode": "edit"})
            else:
                return render(request, "v2/partial/project/details.html",
                              context={"project": project, "mode": mode})
        else:
            projects = Project.objects.order_by("name")
            return render(request, "v2/partial/project/table.html", context={"projects": projects})

    def post(self, request, *args, **kwargs):
        mode = request.GET.get("mode", "view")

        # MetadataFormSet = formset_factory(MetadataTermForm, can_delete=True)

        if mode == "edit":
            project = get_object_or_404(Project, pk=kwargs["id"])
            initial = {"name": project.name, "recordIdColumnName": project.recordIdColumnName,
                       "description": project.description, "abbreviation": project.abbreviation,
                       "externalRecordColumnNames": ",".join(project.externalRecordColumnNames)}
        else:
            project = Project()
            initial = {}
        projectForm = ProjectForm(request.POST, initial=initial)

        if projectForm.is_valid():
            if projectForm.has_changed():
                if "name" in projectForm.changed_data:
                    project.name = projectForm.cleaned_data["name"]
                if "description" in projectForm.changed_data:
                    project.description = projectForm.cleaned_data["description"]
                if "abbreviation" in projectForm.changed_data:
                    project.abbreviation = projectForm.cleaned_data["abbreviation"]
                if "recordIdColumnName" in projectForm.changed_data:
                    project.recordIdColumnName = projectForm.cleaned_data["recordIdColumnName"]
                if "externalRecordColumnNames" in projectForm.changed_data:
                    project.externalRecordColumnNames = projectForm.cleaned_data["externalRecordColumnNames"].split(",")
        project.save()
        return HttpResponseRedirect(reverse('v2:projects'))
