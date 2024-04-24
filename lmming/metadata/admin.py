from django.contrib import admin
from .models import Transfer, Job, Report, Page, ProcessingStep, UrlSettings

admin.site.register(UrlSettings)
admin.site.register(Transfer)
admin.site.register(Job)
admin.site.register(Report)
admin.site.register(Page)
admin.site.register(ProcessingStep)

