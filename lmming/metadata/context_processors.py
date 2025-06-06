from django.conf import settings


def addArchiveInstitution(request):
    return {"ARCHIVE_INST": settings.ARCHIVE_INST}
