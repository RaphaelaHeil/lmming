from django.urls import path

from . import views, partials

app_name = "v2"

urlpatterns = [
    path("", views.index, name="index"),
    path("processes", views.ProcessesView.as_view(), name="process_table"),
    path("process/create", partials.createProcess, name="create_process"),
    path("process/<int:process_id>", views.ProcessView.as_view(), name="process"),
    # path("process/<int:process_id>/download/<str:filetype>", views.downloadProcess, name="download_process"),
    path("processes/delete", partials.batchDeleteModal, name="process_batch_delete"),
    # path("processes/download", views.batchDownload, name="process_batch_export"),
    path("process/modal/delete/<int:process_id>", partials.deleteModal, name="process_delete_modal"),
    # path("process/modal/cancel/<int:transfer_id>", partials.cancelTransferModal, name="process_cancel_modal"),
    # path("processes/redirect/download", partials.batchDownloadRedirect, name="process_batch_redirect"),
    # path("processes/waiting/table", partials.waitingProcesses, name="waiting_reports_table"),
    path("vocabularies", views.VocabularyView.as_view(), name="vocabularies"),
    path("vocabulary", views.VocabularyView.as_view(), name="vocab_create"),
    path("vocabulary/<int:id>", views.VocabularyView.as_view(), name="vocab_view_edit"),
    path("projects", views.ProjectView.as_view(), name="projects"),
    path("project", views.ProjectView.as_view(), name="project_create"),
    path("project/<int:id>", views.ProjectView.as_view(), name="project_view_edit"),
    path("process", partials.createProcess, name="process_create"),
    path("settings", partials.settingsModal, name="settings_modal"),
]
