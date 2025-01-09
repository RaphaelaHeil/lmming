from django.contrib import admin

from .models import ExtractionTransfer, Job, Report, Page, ProcessingStep, DefaultValueSettings, \
    DefaultNumberSettings, ExternalRecord, ReportTranslation, FacSpecificData


class ProcessingStepAdmin(admin.ModelAdmin):
    list_filter = ["processingStepType"]

class JobAdmin(admin.ModelAdmin):
    list_filter = ["status"]
    sortable_by = ["lastUpdated"]

admin.site.register(ExtractionTransfer)
admin.site.register(Job)
admin.site.register(Report)
admin.site.register(Page)
admin.site.register(ProcessingStep, ProcessingStepAdmin)
admin.site.register(DefaultValueSettings)
admin.site.register(DefaultNumberSettings)
admin.site.register(ExternalRecord)
admin.site.register(ReportTranslation)
admin.site.register(FacSpecificData)



