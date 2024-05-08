from django.urls import path

from . import views, partials

app_name = "metadata"

urlpatterns = [
    path("", views.index, name="index"),
    path("transfers", views.Transfers.as_view(), name="transfer_table"),
    path("transfer/create", partials.createTransfer, name="create_transfer"),
    path("transfer/<int:transfer_id>", views.Transfer.as_view(), name="transfer"),
    path("transfer/<int:transfer_id>/verify", partials.verifyTransfer, name="verify_transfer"),
    path("transfers/delete", partials.batchDeleteModal, name="transfer_batch_delete"),
    path("transfer/modal/delete/<int:transfer_id>", partials.deleteModal, name="transfer_delete_modal"),
    path("job/<int:job_id>", views.JobView.as_view(), name="job"),
    path("settings", partials.settingsModal, name="settings_modal"),

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

]
