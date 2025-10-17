from django.shortcuts import render
from django.views.generic import View

from ark.forms import ArkDetails, EditArk, CreateArk
from ark.utils import getArkDetails, updateArk, createArk


def index(request):
    return render(request, "ark/partial/index.html", {})


class Read(View):
    def get(self, request):
        detailform = ArkDetails()
        return render(request, 'ark/partial/arkform.html',
                      {"form": detailform, "mode": "view", "title": "View ARK Details"})

    def post(self, request):
        detailform = ArkDetails(request.POST, initial={})

        if detailform.is_valid():
            if "ark" in detailform.changed_data:
                ark = detailform.cleaned_data["ark"]
                if ark.endswith("?json") or ark.endswith("?info"):
                    ark = ark[:-5]
                try:
                    arkDetails = getArkDetails(ark)
                    context = {k: v["value"] for k, v in arkDetails.items()}
                    context["ark"] = ark
                    return render(request, "ark/partial/details.html", context)
                except ValueError as e:
                    return render(request, "ark/partial/error.html", {"error": str(e)})

        return render(request, 'ark/partial/details.html', {"form": detailform})


class Create(View):
    def get(self, request):
        form = CreateArk(initial={})
        return render(request, "ark/partial/edit.html", {"form": form, "mode": "create"})

    def post(self, request):
        form = CreateArk(request.POST)
        if form.is_valid():
            try:
                response = createArk(form.cleaned_data)
                return render(request, "ark/partial/details.html", response)
            except ValueError as e:
                return render(request, "ark/partial/error.html", {"error": str(e)})

        return render(request, "ark/partial/edit.html", {"form": form, "mode": "create"})


class Edit(View):
    def get(self, request):
        detailform = ArkDetails()
        return render(request, 'ark/partial/arkform.html',
                      {"form": detailform, "mode": "edit", "title": "Edit ARK Details"})

    def post(self, request):
        if "url" not in request.POST:
            context = {"url": "", "title": "", "type": "", "commitment": "", "identifier": "", "format": "",
                       "relation": "",
                       "source": "", "metadata": ""}
            try:
                ark = request.POST["ark"]
                if ark.endswith("?json") or ark.endswith("?info"):
                    ark = ark[:-5]
                arkDetails = getArkDetails(ark)
                context.update({k: v["value"] for k, v in arkDetails.items()})
                context["ark"] = ark
                form = EditArk(initial=context)
            except ValueError as e:
                return render(request, "ark/partial/error.html", {"error": str(e)})
        else:
            form = EditArk(request.POST, initial={})
            ark = request.POST["ark"]
            if ark.endswith("?json") or ark.endswith("?info"):
                ark = ark[:-5]
            if form.is_valid():
                try:
                    response = updateArk(ark, form.cleaned_data)
                    response["ark"] = ark
                    return render(request, "ark/partial/details.html", response)
                except ValueError as e:
                    return render(request, "ark/partial/error.html", {"error": str(e)})
        return render(request, "ark/partial/edit.html", {"form": form, "mode": "edit"})
