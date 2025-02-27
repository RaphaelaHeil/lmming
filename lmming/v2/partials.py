from django.http import QueryDict
from django.shortcuts import render, get_object_or_404

from v2.forms.process import ProcessForm
from v2.models import Project, Process, Item, Page
from v2.tasks.manage import scheduleTask
from v2.utils import extractFileData, initMetadataAssignment, initProcessingSteps


def createProcess(request):
    projects = [(p.name, p.name) for p in Project.objects.all().order_by("name")]

    if request.method == "POST":
        processForm = ProcessForm(request.POST, request.FILES, projects=projects)
        if processForm.is_valid():
            processName = processForm.cleaned_data["name"]
            projectName = processForm.cleaned_data["project"]
            files = processForm.cleaned_data["file_field"]

            data, ids, typeNames, _, dates = extractFileData(files)

            if len(ids) > 1 or len(typeNames) > 1 or len(dates) > 1:
                processForm.error = ("The selected files contain a mix of record IDs, types and/or dates. Please "
                                     "ensure that the selected files all carry the same information for "
                                     "these fields, i.e. that the filenames only differ by page number and (possibly) "
                                     "extension.")
                return render(request, 'v2/partial/process/create.html', {"form": processForm})

            process = Process.objects.create(name=processName, project=Project.objects.get(name=projectName))
            item = Item.objects.create(process=process, recordId=ids.pop(), documentTypeIdentifier=typeNames.pop(),
                                       date=list(dates.pop()))
            pages = []
            for fileData in data:
                p = Page.objects.create(item=item, originalFilename=fileData["file"], file=fileData["file"],
                                        fileType=fileData["fileType"], pageNumber=fileData["page"])
                pages.append(p)

            initMetadataAssignment(process, item, pages)

            initProcessingSteps(process)

            return render(request, 'v2/partial/index_partial.html')
    else:
        processForm = ProcessForm(projects=projects)
    return render(request, 'v2/partial/process/create.html', {"form": processForm})


def deleteModal(request, process_id):
    process = get_object_or_404(Process, pk=process_id)
    return render(request, "v2/modal/delete_process.html", {"process": process})


def batchDeleteModal(request):
    ids = [int(id) for id in (QueryDict(request.body).getlist("ids"))]
    result = ""
    if ids:
        result = f"ids={ids[0]}"
        for ID in ids[1:]:
            result += f"&ids={ID}"
    return render(request, "v2/modal/bulk_delete.html",
                  {"ids": result, "processes": (Process.objects.filter(id__in=ids))})


def settingsModal(request):
    pass
