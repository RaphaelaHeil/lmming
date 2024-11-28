from django.urls import path

from . import views

app_name = "ark"

urlpatterns = [
    path("", views.index, name="index"),
    path("view", views.Read.as_view(), name="view"),
    path("create", views.Create.as_view(), name="create"),
    path("edit", views.Edit.as_view(), name="edit"),
]
