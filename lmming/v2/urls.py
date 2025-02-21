from django.urls import path

from . import views

app_name = "v2"

urlpatterns = [
    path("", views.index, name="index"),
    path("vocabularies", views.VocabularyView.as_view(), name="vocabularies"),
    path("vocabulary", views.VocabularyView.as_view(), name="vocab_create"),
    path("vocabulary/<int:id>", views.VocabularyView.as_view(), name="vocab_view_edit"),
    path("projects", views.ProjectView.as_view(), name="projects"),
    path("project", views.ProjectView.as_view(), name="project_create"),
    path("project/<int:id>", views.ProjectView.as_view(), name="project_view_edit"),
]
