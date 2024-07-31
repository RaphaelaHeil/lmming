from datetime import date
from pathlib import Path
from unittest import mock

from django.test import TestCase
from pyhandle.handleexceptions import HandleAlreadyExistsException

from metadata.models import Report, ProcessingStep, Status
from metadata.tasks.arab import arabComputeFromExistingFields, arabMintHandle
from metadata.test.utils import initDefaultValues, initDummyTransfer, initDummyFilemaker, TEST_PAGES


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


def handleAlreadyExists(*_args, **_kwards):
    raise HandleAlreadyExistsException(msg="already exists")


def mintSuccess(*_args, **_kwargs):
    return "12345/PID"


def mockPIDGen(*_args, **_kwargs):
    return "PID"


class ArabMintHandleTests(TestCase):

    @mock.patch("pyhandle.client.resthandleclient.RESTHandleClient.generate_PID_name", side_effect=mockPIDGen)
    @mock.patch("pyhandle.client.resthandleclient.RESTHandleClient.register_handle_kv", side_effect=mintSuccess)
    def test_mintSuccess(self, mockSuccess, mockPidGen):
        a = Path("./metadata/test/cert_test.pem").resolve()
        with self.settings(ARAB_HANDLE_OWNER="100:12345/12354", ARAB_HANDLE_PREFIX="12345",
                           IIIF_BASE_URL="http://iiif.example.com", ARAB_PRIVATE_KEY_FILE=str(a),
                           ARAB_CERTIFICATE_FILE=str(a)):
            initDefaultValues({"yearOffset": -1, "language": "test", "license": "license"})
            initDummyFilemaker()
            jobId = initDummyTransfer(archive="ARAB")

            arabMintHandle(jobId, False)

            r = Report.objects.get(job=jobId)

            self.assertEqual("PID", r.noid)
            self.assertEqual("https://hdl.handle.net/12345/PID", r.identifier)
            for page in r.page_set.all():
                self.assertEqual(f"PID_{page.order}", page.iiifId)
                self.assertEqual(f"http://iiif.example.com/iiif/image/PID_{page.order}/info.json", page.identifier)

    @mock.patch("pyhandle.client.resthandleclient.RESTHandleClient.register_handle_kv", side_effect=handleAlreadyExists)
    def test_exceedRetries(self, mockException):
        a = Path("./metadata/test/cert_test.pem").resolve()
        with self.settings(ARAB_HANDLE_OWNER="100:12345/12354", ARAB_HANDLE_PREFIX="12345",
                           IIIF_BASE_URL="http://iiif.example.com", ARAB_PRIVATE_KEY_FILE=str(a),
                           ARAB_CERTIFICATE_FILE=str(a)):
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