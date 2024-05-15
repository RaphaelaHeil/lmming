from django.contrib import admin
from .models import ExtractionTransfer, Job, Report, Page, ProcessingStep, UrlSettings, DefaultValueSettings, \
    DefaultNumberSettings, FilemakerEntry

admin.site.register(UrlSettings)
admin.site.register(ExtractionTransfer)
admin.site.register(Job)
admin.site.register(Report)
admin.site.register(Page)
admin.site.register(ProcessingStep)
admin.site.register(DefaultValueSettings)
admin.site.register(DefaultNumberSettings)
admin.site.register(FilemakerEntry)
