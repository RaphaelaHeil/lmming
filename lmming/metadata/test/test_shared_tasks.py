import logging
from pathlib import Path
from unittest import mock

from django.test import TestCase

from metadata.models import Report, ProcessingStep, Status, Page
from metadata.nlp.ner import NlpResult
from metadata.tasks.shared import fileMakerLookup, namedEntityRecognition
from metadata.test.utils import initDefaultValues, initDummyTransfer, initDummyFilemaker


class FilemakerLookupTests(TestCase):

    def tearDown(self):
        for page in Page.objects.all():
            page.delete()

    def test_Task(self):
        initDefaultValues()
        initDummyFilemaker()
        jobId = initDummyTransfer(reportData={"unionId": "1"})
        fileMakerLookup(jobId, False)

        r = Report.objects.get(job=jobId)

        self.assertEqual("Test Orga", r.creator)
        self.assertEqual(["http://nadLink.example.com"], r.relation)
        self.assertEqual(["SE", "county", "municipality", "city", "parish"], r.spatial)
        self.assertEqual("OTHER", r.coverage)

    def test_missingOrganisationName(self):
        initDefaultValues()
        initDummyFilemaker({"archiveId": "1"})
        jobId = initDummyTransfer(reportData={"unionId": "1"})
        fileMakerLookup(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("Organisation name", step.log)

    def test_missingSpatial(self):
        initDefaultValues()
        initDummyFilemaker({"archiveId": "1"})
        jobId = initDummyTransfer(reportData={"unionId": "1"})
        fileMakerLookup(jobId, False)

        r = Report.objects.get(job=jobId)

        self.assertEqual(["SE"], r.spatial)

    def test_unknownUnionId(self):
        initDefaultValues()
        initDummyFilemaker()
        jobId = initDummyTransfer(reportData={"unionId": "2"})
        fileMakerLookup(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("union with ID 2", step.log)


def successfulNer(path: Path):
    if "sid-01" in path.name:
        return NlpResult(text="new text", normalised="new normalised", persons={"A", "B"}, organisations={"o"},
                         locations={"l1"}, times={"1991"}, works={"lotr"}, events={"easter"}, objects={"statue"},
                         measures=True)
    else:
        return NlpResult(text="second text", normalised="second normalised", persons={"C"}, organisations={"WTO"},
                         locations={"l2"}, times={"2020"}, works={"hobbit"}, events={"christmas"}, objects={"painting"},
                         measures=False)


def failedNer(_path: Path):
    raise ValueError("test")


class NamedEntityRecognitionTests(TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        for page in Page.objects.all():
            page.delete()

    @mock.patch("metadata.tasks.shared.processPage", side_effect=successfulNer)
    def test_ner(self, _successfulNerMock):
        initDefaultValues()
        initDummyFilemaker()
        jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

        namedEntityRecognition(jobId, False)
        r = Report.objects.get(job=jobId)

        page1 = Page.objects.get(report=r.id, order=1)
        page2 = Page.objects.get(report=r.id, order=2)

        self.assertEqual("new text", page1.transcription)
        self.assertTrue(page1.measures)

        self.assertEqual("second text", page2.transcription)
        self.assertFalse(page2.measures)

    @mock.patch("metadata.tasks.shared.processPage", side_effect=failedNer)
    def test_failedNer(self, _failedNerMock):
        initDefaultValues()
        initDummyFilemaker()
        jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

        namedEntityRecognition(jobId, False)

        r = Report.objects.get(job=jobId)

        page1 = Page.objects.get(report=r.id, order=1)
        page2 = Page.objects.get(report=r.id, order=2)

        self.assertEqual("", page1.transcription)
        self.assertFalse(page1.measures)

        self.assertEqual("", page2.transcription)
        self.assertFalse(page2.measures)
