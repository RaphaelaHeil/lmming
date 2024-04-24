from django.urls import path

from . import views, partials

app_name = "metadata"

urlpatterns = [
    path("", views.index, name="index"),
    path("transfers", views.Transfers.as_view(), name="transfer_table"),
    # path("jobs", name="job_table")
    # path("jobs", views.Jobs.as_view(), name="job_table"),
    # path("jobs/results", views.batchDownloadNERResults, name="batch_download"),
    # path("jobs/create", partials.createBatchJob, name="bulk_upload"),
    # path("job/create", partials.createSimpleJob, name="create_job"),
    # path("job/<int:jobId>", views.JobView.as_view(), name="single_job"),
    # path("job/<int:jobId>/result", views.downloadNerResult, name="download"),
    # path("settings", views.modelSettings, name="model_settings"),
    # path("modal/delete/<int:jobId>", partials.deleteModal, name="delete_modal"),
    # path("modal/jobs/download", partials.batchDownloadModal, name="batch_download_modal"),
    # path("modal/jobs/delete", partials.batchDeleteModal, name="batch_delete_modal"),
]
