from copy import deepcopy
from datetime import date
from typing import Dict, List, Any

from django.core.files.uploadedfile import SimpleUploadedFile

from metadata.models import Report, Page, DefaultValueSettings, ExtractionTransfer, DefaultNumberSettings, Job, \
    FilemakerEntry
from metadata.partials import __buildProcessingSteps__

TEST_REPORT = {"identifier": "http://ark.example.com/ark:/12345/testbcd/manifest", "title": "title",
               "creator": "creator", "date": [date(1991, 1, 1)], "coverage": "workplace", "language": ["sv"],
               "spatial": ["SE"], "type": ["ANNUAL_REPORT"], "license": ["license", "url to def"],
               "isVersionOf": "http://atom.example.com", "isFormatOf": ["printed"],
               "relation": ["relation", "relation url"], "created": date(1992, 1, 1), "available": date(2082, 1, 1),
               "accessRights": "RESTRICTED", "source": ["source", "source url"], "description": "dummy description",
               "unionId": "1", "noid": "testbcd"}

TEST_PAGES = [{"order": 1,
               "transcriptionFile": SimpleUploadedFile("fac_00001_arsberattelse_1991_sid-01.xml",
                                                       b"these are the file contents!"),
               "originalFileName": "fac_00001_arsberattelse_1991_sid-01.xml",
               "identifier": "http://iiif.example.com/page1", "transcription": "transcription",
               "normalisedTranscription": "normalised transcription", "persons": ["person A", "person B"],
               "organisations": ["org 1", "org 2"], "locations": ["l1", "l2"],
               "times": ["time A", "time B"], "events": ["event A", "event B"],
               "ner_objects": ["object1", "object2"], "measures": True, "iiifId": "testbcd_1"},
              {"order": 2,
               "transcriptionFile": SimpleUploadedFile("fac_00001_arsberattelse_1991_sid-02.xml",
                                                       b"these are the file contents!"),
               "originalFileName": "fac_00001_arsberattelse_1991_sid-02.xml",
               "identifier": "http://iiif.example.com/page1", "transcription": "transcription",
               "normalisedTranscription": "normalised transcription", "persons": ["person A", "person B"],
               "organisations": ["org 1", "org 2"], "locations": ["l1", "l2"],
               "times": ["time A", "time B"], "events": ["event A", "event B"],
               "ner_objects": ["object1", "object2"], "measures": True, "iiifId": "testbcd_2"}
              ]

DEFAULT_VALUES = {"license": "license", "language": "language", "source": "source", "accessRights": "RESTRICTED",
                  "arkShoulder": "/test", "yearOffset": 70}


def initDefaultValues(values: Dict[str, Any] = None):
    if values is None:
        values = deepcopy(DEFAULT_VALUES)

    if "license" in values:
        DefaultValueSettings.objects.create(name=DefaultValueSettings.DefaultValueSettingsType.DC_LICENSE,
                                            value=values["license"])
    if "language" in values:
        DefaultValueSettings.objects.create(name=DefaultValueSettings.DefaultValueSettingsType.DC_LANGUAGE,
                                            value=values["language"])
    if "source" in values:
        DefaultValueSettings.objects.create(name=DefaultValueSettings.DefaultValueSettingsType.DC_SOURCE,
                                            value=values["source"])

    if "accessRights" in values:
        DefaultValueSettings.objects.create(name=DefaultValueSettings.DefaultValueSettingsType.DC_ACCESS_RIGHTS,
                                            value=values["accessRights"])

    if "arkShoulder" in values:
        DefaultValueSettings.objects.create(name=DefaultValueSettings.DefaultValueSettingsType.ARK_SHOULDER,
                                            value=values["arkShoulder"])

    if "yearOffset" in values:
        DefaultNumberSettings.objects.create(name=DefaultNumberSettings.DefaultNumberSettingsType.AVAILABLE_YEAR_OFFSET,
                                             value=values["yearOffset"])


def initDummyFilemaker(filemakerEntry: Dict[str, Any] = None):
    if filemakerEntry is None:
        FilemakerEntry.objects.create(archiveId="1", organisationName="Test Orga", county="county",
                                      municipality="municipality", city="city", parish="parish",
                                      nadLink="http://nadLink.example.com")
    else:
        FilemakerEntry.objects.create(**filemakerEntry)


def initDummyTransfer(reportData: Dict[str, Any] = None, pageData: List[Dict[str, Any]] = None):
    et = ExtractionTransfer.objects.create(name="TestTransfer")

    # unionId="1", type=[Report.DocumentType.ANNUAL_REPORT], date=[date(1991, 1, 1)],

    if reportData is None:
        reportData = deepcopy(TEST_REPORT)
    if not "unionId" in reportData:
        reportData["unionId"] = "1"
    if pageData is None:
        pageData = deepcopy(TEST_PAGES)

    report = Report.objects.create(transfer=et, **reportData)
    for page in pageData:
        Page.objects.create(report=report, **page)

    job = Job.objects.create(transfer=et, report=report)

    report.job = job
    report.save()

    data = {"filenameMode": "Automatic", "filenameHumVal": False,
            "filemakerMode": "Automatic", "filemakerHumVal": False,
            "generateMode": "Automatic", "generateHumVal": False,
            "facManualMode": "Manual", "facManualHumVal": False,
            "nerMode": "Automatic", "nerHumVal": False,
            "mintMode": "Automatic", "mintHumVal": False, }
    steps = __buildProcessingSteps__(data, job)

    return job.pk
