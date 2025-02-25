from django.contrib import admin

from v2.models import Vocabulary, MetadataTerm, Project, ProjectMetadataTerm, BasicValueType, ChoiceValueType, \
    ExternalRecordField, ExternalRecordEntry, ProcessingStepConfiguration, Process, Item, Page, ProcessingStep, \
    MetadataAssignment, TextValue, DateValue, PlainHandleValue, LocationHandleValue, Location

admin.site.register(Vocabulary)
admin.site.register(MetadataTerm)
admin.site.register(Project)
admin.site.register(ProjectMetadataTerm)
admin.site.register(BasicValueType)
admin.site.register(ChoiceValueType)
admin.site.register(ExternalRecordEntry)
admin.site.register(ExternalRecordField)
admin.site.register(ProcessingStepConfiguration)
admin.site.register(Process)
admin.site.register(Item)
admin.site.register(Page)
admin.site.register(ProcessingStep)
admin.site.register(MetadataAssignment)
admin.site.register(TextValue)
admin.site.register(DateValue)
admin.site.register(PlainHandleValue)
admin.site.register(LocationHandleValue)
admin.site.register(Location)
