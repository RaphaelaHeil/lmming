from django.urls import path

from . import views, partials

app_name = "metadata"

urlpatterns = [
    path("", views.index, name="index"),
    path("transfers", views.Transfers.as_view(), name="transfer_table"),
    path("transfer/create", partials.createTransfer, name="create_transfer"),
    path("transfer/<int:transfer_id>", views.Transfer.as_view(), name="transfer"),
    path("transfer/<int:transfer_id>/verify", partials.verifyTransfer, name="verify_transfer"),
    path("transfer/<int:transfer_id>/download/<str:filetype>", views.downloadTransfer, name="download_transfer"),
    path("transfers/delete", partials.batchDeleteModal, name="transfer_batch_delete"),
    path("transfer/modal/delete/<int:transfer_id>", partials.deleteModal, name="transfer_delete_modal"),
    path("transfer/modal/cancel/<int:transfer_id>", partials.cancelTransferModal, name="transfer_cancel_modal"),
    path("job/<int:job_id>", views.jobDetails, name="job"),
    path("job/<int:job_id>/edit/<str:step>", views.JobEditView.as_view(), name="edit_job"),
    path("job/<int:job_id>/restart/<str:step>", partials.restart, name="restart"),
    path("settings", partials.settingsModal, name="settings_modal"),
    path("jobs/waiting", views.waitingJobs, name="waiting_jobs"),
    path("jobs/waiting/table", partials.awaitingHumanInteraction, name="waiting_jobs_table"),
    path("jobs/waiting/count", partials.waitingCount, name="waiting_count")
]
