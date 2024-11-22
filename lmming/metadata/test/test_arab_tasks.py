from datetime import date
from pathlib import Path
from unittest import mock

from django.test import TestCase

from metadata.models import Report, ProcessingStep, Status, Page
from metadata.tasks.arab import arabComputeFromExistingFields, arabMintHandle
from metadata.test.utils import initDefaultValues, initDummyTransfer, initDummyFilemaker, TEST_PAGES


class ArabComputeFromExistingFieldsTests(TestCase):

    def tearDown(self):
        for page in Page.objects.all():
            page.delete()

    def test_noPages(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report, pageData=[], archive="ARAB")

        arabComputeFromExistingFields(jobId, False)
        r = Report.objects.get(job=jobId)

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


class MockResponse:
    def __init__(self, json_data, status_code, ok):
        self.json_data = json_data
        self.status_code = status_code
        self.ok = ok

    def json(self):
        return self.json_data


def mockGet(*_args, **kwargs):
    url = kwargs["url"]
    if "handles" in url:
        return MockResponse("", 200, False)
    if "sessions/this" in url:
        return MockResponse({"sesionId": "abc", "nonce": "c2VydmVybm9uY2U="})


def mockGetHandleExists(*_args, **kwargs):
    url = kwargs["url"]
    if "handles" in url:
        return MockResponse({}, 200, True)
    if "sessions/this" in url:
        return MockResponse({"sesionId": "abc", "nonce": "c2VydmVybm9uY2U="})


def mockPost(*_args, **kwargs):
    url = kwargs["url"]
    if "this" in url:
        return MockResponse({}, 200, True)
    if "sessions" in url:
        return MockResponse({"sessionId": "abc", "nonce": "c2VydmVybm9uY2U="}, 200, True)


def mockPut(*_args, **_kwargs):
    return MockResponse({}, 200, True)


def mockPIDGen(*_args, **_kwargs):
    return "x"


def mockSign(*_args, **_kwargs):
    return b"sign"


class ArabMintHandleTests(TestCase):

    def tearDown(self):
        for page in Page.objects.all():
            page.delete()

    @mock.patch("metadata.tasks.utils.signBytesSHA256", side_effect=mockSign)
    @mock.patch("requests.get", side_effect=mockGet)
    @mock.patch("requests.post", side_effect=mockPost)
    @mock.patch("requests.put", side_effect=mockPut)
    @mock.patch("secrets.choice", side_effect=mockPIDGen)
    def test_mintSuccess(self, _mockPidGen, _mockPut, _mockPost, _mockGet, _mockSign):
        with self.settings(ARAB_HANDLE_PREFIX="12345", IIIF_BASE_URL="http://iiif.example.com",
                           ARAB_PRIVATE_KEY_FILE=str(Path("./metadata/test/cert_test.pem").resolve()),
                           ARAB_HANDLE_IP="127.0.0.1", ARAB_HANDLE_PORT=8000, ARAB_HANDLE_ADMIN="0.NA/6789",
                           ARCHIVE_INST="ARAB", ARAB_RETRIES=3, ARAB_HANDLE_ADDRESS="hdl.example.com", ARAB_CERT_FILE="file.dummy"):
            initDefaultValues({"yearOffset": -1, "language": "test", "license": "license"})
            initDummyFilemaker()
            jobId = initDummyTransfer(archive="ARAB", reportData={})

            arabMintHandle(jobId, False)

            r = Report.objects.get(job=jobId)

            self.assertEqual("xxxxxxxxxxxxxxx", r.noid)
            self.assertEqual("https://hdl.handle.net/12345/xxxxxxxxxxxxxxx?urlappend=/manifest", r.identifier)
            for page in r.page_set.all():
                self.assertEqual(f"xxxxxxxxxxxxxxx_{page.order}", page.iiifId)
                self.assertEqual(f"http://iiif.example.com/iiif/image/xxxxxxxxxxxxxxx_{page.order}/info.json",
                                 page.identifier)

    @mock.patch("requests.post", side_effect=mockPost)
    @mock.patch("requests.get", side_effect=mockGetHandleExists)
    def test_exceedRetries(self, _mockGet, _mockPost):
        with self.settings(ARCHIVE_INST="ARAB", ARAB_HANDLE_PREFIX="12345", IIIF_BASE_URL="http://iiif.example.com",
                           ARAB_PRIVATE_KEY_FILE=str(Path("./metadata/test/cert_test.pem").resolve()),
                           ARAB_HANDLE_IP="127.0.0.1", ARAB_HANDLE_PORT=8000, ARAB_HANDLE_ADMIN="0.NA/6789",
                           ARAB_RETRIES=3, ARAB_HANDLE_ADDRESS="hdl.example.com", ARAB_CERT_FILE="file.dummy"):
            initDefaultValues({"yearOffset": -1, "language": "test", "license": "license"})
            initDummyFilemaker()
            jobId = initDummyTransfer(archive="ARAB", reportData={})

            arabMintHandle(jobId, False)

            step = ProcessingStep.objects.get(job_id=jobId,
                                              processingStepType=ProcessingStep.ProcessingStepType.ARAB_MINT_HANDLE.value)
            self.assertEqual(step.status, Status.ERROR)
            self.assertIn("unique handle", step.log)
            r = Report.objects.get(job=jobId)

            self.assertEqual("", r.noid)
            self.assertEqual(None, r.identifier)
