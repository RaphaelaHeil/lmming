from django.contrib import admin

from v2.models import Vocabulary, MetadataTerm, Project, ProjectMetadataTerm, BasicValueType, ChoiceValueType, \
    ExternalRecordField, ExternalRecordEntry

admin.site.register(Vocabulary)
admin.site.register(MetadataTerm)
admin.site.register(Project)
admin.site.register(ProjectMetadataTerm)
admin.site.register(BasicValueType)
admin.site.register(ChoiceValueType)
admin.site.register(ExternalRecordEntry)
admin.site.register(ExternalRecordField)
