from datetime import date

from django.test import TestCase

from metadata.models import Report, ProcessingStep, Status
from metadata.tasks.arab import arabComputeFromExistingFields
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
