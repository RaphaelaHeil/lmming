import logging
from datetime import date
from pathlib import Path
from unittest import mock

from django.test import TestCase

from metadata.models import Report, ProcessingStep, Status, Page
from metadata.nlp.ner import NlpResult
from metadata.tasks import computeFromExistingFields, fileMakerLookup, mintArks, namedEntityRecognition, \
    arabComputeFromExistingFields
from metadata.test.utils import initDefaultValues, initDummyTransfer, initDummyFilemaker, TEST_PAGES


class FilemakerLookupTests(TestCase):

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


class ComputeFromExistingFieldsTests(TestCase):

    def test_noPages(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report, pageData=[])

        computeFromExistingFields(jobId, False)
        r = Report.objects.get(job=jobId)

        self.assertEqual("Test Union - annual report (1991)", r.title)
        self.assertEqual(date(1992, 1, 1), r.created)
        self.assertEqual(["language"], r.language)
        self.assertEqual("0 pages", r.description)
        self.assertEqual(date(2062, 1, 1), r.available)
        self.assertEqual(["license"], r.license)
        self.assertEqual("RESTRICTED", r.accessRights)

    def test_onePage(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report, pageData=[TEST_PAGES[0]])

        computeFromExistingFields(jobId, False)
        r = Report.objects.get(job=jobId)

        self.assertEqual("Test Union - annual report (1991)", r.title)
        self.assertEqual(date(1992, 1, 1), r.created)
        self.assertEqual(["language"], r.language)
        self.assertEqual("1 page", r.description)
        self.assertEqual(date(2062, 1, 1), r.available)
        self.assertEqual(["license"], r.license)
        self.assertEqual("RESTRICTED", r.accessRights)

    def test_severalPages(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report)

        computeFromExistingFields(jobId, False)
        r = Report.objects.get(job=jobId)

        self.assertEqual("Test Union - annual report (1991)", r.title)
        self.assertEqual(date(1992, 1, 1), r.created)
        self.assertEqual(["language"], r.language)
        self.assertEqual("2 pages", r.description)
        self.assertEqual(date(2062, 1, 1), r.available)
        self.assertEqual(["license"], r.license)
        self.assertEqual("RESTRICTED", r.accessRights)

    def test_noLanguage(self):
        initDefaultValues({"language": ""})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("language", step.log)

    def test_emptyLicense(self):
        initDefaultValues({"license": "", "language": "test"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("license", step.log)

    def test_noLicense(self):
        initDefaultValues({"language": "test"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("license", step.log)

    def test_noYearOffset(self):
        initDefaultValues({"language": "test", "license": "license"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("offset", step.log)

    def test_negativeYearOffset(self):
        initDefaultValues({"yearOffset": -1, "language": "test", "license": "license"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("offset is negative", step.log)


class MockResponse:
    def __init__(self, json_data, status_code, ok):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = ok

    def json(self):
        return self.json_data


def successfulPost(*args, **kwargs):
    return MockResponse({"ark": "ark:/12345/testabc"}, 200, True)


def successfulPut(*args, **kwargs):
    return MockResponse({"ark": "ark:/12345/testabc"}, 200, True)


def failedPost(*args, **kwargs):
    return MockResponse({}, 404, False)


def failedPut(*args, **kwargs):
    return MockResponse({}, 404, False)


class MintArkTests(TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    @mock.patch('requests.put', side_effect=successfulPut)
    @mock.patch('requests.post', side_effect=successfulPost)
    def test_task(self, mockPost, mockPut):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues()
            initDummyFilemaker()
            jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

            mintArks(jobId, False)

            r = Report.objects.get(job=jobId)
            self.assertEqual("testabc", r.noid)
            self.assertEqual("https://ark.fauppsala.se/ark:/12345/testabc/manifest", r.identifier)
            self.assertIn(mock.call('http://example.com/mint', headers={"Authorization": "Bearer auth"},
                                    json={"naan": "12345", "shoulder": "/test"}), mockPost.call_args_list)

            self.assertIn(mock.call(url='http://example.com/update', headers={"Authorization": "Bearer auth"},
                                    json={"ark": "ark:/12345/testabc", "title": "test title",
                                          "url": "http://iiif.example.com/iiif/presentation/testabc"}),
                          mockPut.call_args_list)

            for page in r.page_set.all():
                self.assertEqual(f"testabc_{page.order}", page.iiifId)

    def test_missingShoulder(self):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues({})
            initDummyFilemaker()
            jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

            mintArks(jobId, False)

            step = ProcessingStep.objects.get(job_id=jobId,
                                              processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value)
            self.assertEqual(step.status, Status.ERROR)
            self.assertIn("ARK Shoulder is not set", step.log)

    def test_emptyShoulder(self):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues({"arkShoulder": ""})
            initDummyFilemaker()
            jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

            mintArks(jobId, False)

            step = ProcessingStep.objects.get(job_id=jobId,
                                              processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value)
            self.assertEqual(step.status, Status.ERROR)
            self.assertIn("ARK Shoulder is empty", step.log)

    def test_invalidShoulder(self):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues({"arkShoulder": "invalid"})
            initDummyFilemaker()
            jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

            mintArks(jobId, False)

            step = ProcessingStep.objects.get(job_id=jobId,
                                              processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value)
            self.assertEqual(step.status, Status.ERROR)
            self.assertIn("should start with a slash", step.log)

    @mock.patch('requests.post', side_effect=failedPost)
    def test_mintingFailur(self, failedPost):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues()
            initDummyFilemaker()
            jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

            mintArks(jobId, False)

            r = Report.objects.get(job=jobId)
            self.assertEqual("", r.noid)

            step = ProcessingStep.objects.get(job_id=jobId,
                                              processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value)
            self.assertEqual(step.status, Status.ERROR)
            self.assertIn("error occurred while obtaining a new ARK", step.log)

    @mock.patch('requests.put', side_effect=failedPut)
    @mock.patch('requests.post', side_effect=successfulPost)
    def test_updateFailure(self, successfulPost, failedPut):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues()
            initDummyFilemaker()
            jobId = initDummyTransfer({"unionId": "1", "title": "test title"})

            mintArks(jobId, False)

            r = Report.objects.get(job=jobId)
            self.assertEqual("testabc", r.noid)
            for page in r.page_set.all():
                self.assertEqual(f"testabc_{page.order}", page.iiifId)

            self.assertEqual("https://ark.fauppsala.se/ark:/12345/testabc/manifest", r.identifier)
            self.assertIn(mock.call('http://example.com/mint', headers={"Authorization": "Bearer auth"},
                                    json={"naan": "12345", "shoulder": "/test"}), successfulPost.call_args_list)

            step = ProcessingStep.objects.get(job_id=jobId,
                                              processingStepType=ProcessingStep.ProcessingStepType.MINT_ARKS.value)
            self.assertEqual(step.status, Status.ERROR)
            self.assertIn("error occurred while updating the ARK", step.log)

    @mock.patch('requests.put', side_effect=successfulPut)
    @mock.patch('requests.post', side_effect=successfulPost)
    def test_existingNoid(self, successfulPost, successfulPut):
        with self.settings(MINTER_URL="http://example.com", MINTER_ORG_ID="12345",
                           IIIF_BASE_URL="http://iiif.example.com", MINTER_AUTH="auth"):
            initDefaultValues()
            initDummyFilemaker()
            jobId = initDummyTransfer()

            mintArks(jobId, False)

            r = Report.objects.get(job=jobId)
            self.assertEqual("testbcd", r.noid)
            self.assertEqual("http://ark.example.com/ark:/12345/testbcd/manifest", r.identifier)
            self.assertFalse(successfulPost.called)
            self.assertIn(mock.call(url='http://example.com/update', headers={"Authorization": "Bearer auth"},
                                    json={"ark": "ark:/12345/testbcd", "title": "title",
                                          "url": "http://iiif.example.com/iiif/presentation/testbcd"}),
                          successfulPut.call_args_list)


def successfulNerMock(path: Path):
    if "sid-01" in path.name:
        return NlpResult(text="new text", normalised="new normalised", persons={"A", "B"}, organisations={"o"},
                         locations={"l1"}, times={"1991"}, works={"lotr"}, events={"easter"}, objects={"statue"},
                         measures=True)
    else:
        return NlpResult(text="second text", normalised="second normalised", persons={"C"}, organisations={"WTO"},
                         locations={"l2"}, times={"2020"}, works={"hobbit"}, events={"christmas"}, objects={"painting"},
                         measures=False)


def failedNerMock(path: Path):
    raise ValueError("test")


class NamedEntityRecognitionTests(TestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    @mock.patch("metadata.tasks.processPage", side_effect=successfulNerMock)
    def test_ner(self, successfulNerMock):
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

    @mock.patch("metadata.tasks.processPage", side_effect=failedNerMock)
    def test_failedNer(self, failedNerMock):
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


class ArabComputeFromExistingFieldsTests(TestCase):

    def test_noPages(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report, pageData=[], archive="ARAB")

        arabComputeFromExistingFields(jobId, False)
        r = Report.objects.get(job=jobId)

        self.assertEqual("Annual Report 1991", r.title)
        self.assertEqual(date(1992, 1, 1), r.created)
        self.assertEqual(["sv"], r.language)
        self.assertEqual("", r.description)
        self.assertEqual(date(2062, 1, 1), r.available)
        self.assertEqual(["license"], r.license)
        self.assertEqual("RESTRICTED", r.accessRights)

    def test_onePage(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report, pageData=[TEST_PAGES[0]], archive="ARAB")

        arabComputeFromExistingFields(jobId, False)
        r = Report.objects.get(job=jobId)

        self.assertEqual("Annual Report 1991", r.title)
        self.assertEqual(date(1992, 1, 1), r.created)
        self.assertEqual(["sv"], r.language)
        self.assertEqual("", r.description)
        self.assertEqual(date(2062, 1, 1), r.available)
        self.assertEqual(["license"], r.license)
        self.assertEqual("RESTRICTED", r.accessRights)

    def test_emptyLicense(self):
        initDefaultValues({"license": "", "language": "test"})
        initDummyFilemaker()
        jobId = initDummyTransfer(archive="ARAB")

        arabComputeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.ARAB_GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("license", step.log)

    def test_noLicense(self):
        initDefaultValues({"language": "test"})
        initDummyFilemaker()
        jobId = initDummyTransfer(archive="ARAB")

        arabComputeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.ARAB_GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("license", step.log)

    def test_noYearOffset(self):
        initDefaultValues({"language": "test", "license": "license"})
        initDummyFilemaker()
        jobId = initDummyTransfer(archive="ARAB")

        arabComputeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.ARAB_GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("offset", step.log)

    def test_negativeYearOffset(self):
        initDefaultValues({"yearOffset": -1, "language": "test", "license": "license"})
        initDummyFilemaker()
        jobId = initDummyTransfer(archive="ARAB")

        arabComputeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId,
                                          processingStepType=ProcessingStep.ProcessingStepType.ARAB_GENERATE.value)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("offset is negative", step.log)
