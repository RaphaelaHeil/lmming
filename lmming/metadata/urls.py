from django.urls import path

from . import views, partials

app_name = "metadata"

urlpatterns = [
    path("", views.index, name="index"),
    path("arab", views.arabIndex, name="arab_index"),
    path("transfers", views.Transfers.as_view(), name="transfer_table"),
    path("transfer/create", partials.createTransfer, name="create_transfer"),
    path("transfer/import", partials.importTransfer, name="import_transfer"),
    path("transfer/<int:transfer_id>", views.Transfer.as_view(), name="transfer"),
    path("transfer/<int:transfer_id>/verify", partials.verifyTransfer, name="verify_transfer"),
    path("transfer/<int:transfer_id>/download/<str:filetype>", views.downloadTransfer, name="download_transfer"),
    path("transfers/delete", partials.batchDeleteModal, name="transfer_batch_delete"),
    path("transfers/download", views.batchDownload, name="transfer_batch_export"),
    path("transfer/modal/delete/<int:transfer_id>", partials.deleteModal, name="transfer_delete_modal"),
    path("transfer/modal/cancel/<int:transfer_id>", partials.cancelTransferModal, name="transfer_cancel_modal"),
    path("transfers/redirect/download", partials.batchDownloadRedirect, name="transfer_batch_redirect"),
    path("transfers/waiting/table", partials.waitingProcesses, name="waiting_reports_table"),
    path("job/<int:job_id>", views.jobDetails, name="job"),
    path("job/<int:job_id>/edit/<str:step>", views.JobEditView.as_view(), name="edit_job"),
    path("job/<int:job_id>/restart/<str:step>", partials.restart, name="restart"),
    path("settings", partials.settingsModal, name="settings_modal"),
    path("jobs/waiting", views.waitingJobs, name="waiting_jobs"),
    path("jobs/waiting/table", partials.awaitingHumanInteraction, name="waiting_jobs_table"),
    path("jobs/waiting/count", partials.waitingCount, name="waiting_count"),
    path("jobs/edit/<str:step>/<str:jobs>", partials.bulkEditJobs, name="bulk_edit_jobs"),
    path("transfers/run", partials.batchRunTable, name="batch_run_table"),
    path("transfers/runs", partials.batchRestart, name="batch_run"),
]
