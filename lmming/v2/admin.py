from django.contrib import admin

from v2.models import Vocabulary, MetadataTerm, Project

admin.site.register(Vocabulary)
admin.site.register(MetadataTerm)
admin.site.register(Project)
