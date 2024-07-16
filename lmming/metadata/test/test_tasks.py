from datetime import date

from django.test import TestCase

from metadata.models import Report, ProcessingStep, Status
from metadata.tasks import computeFromExistingFields
from metadata.test.utils import initDefaultValues, initDummyTransfer, initDummyFilemaker, __TEST_PAGES__


class ComputeFromExistingFields(TestCase):

    def test_noPages(self):
        initDefaultValues()
        initDummyFilemaker()
        report = {"creator": "Test Union", "type": [Report.DocumentType.ANNUAL_REPORT], "date": [date(1991, 1, 1)]}

        jobId = initDummyTransfer(reportData=report, pageData=[])
        r = Report.objects.get(job=jobId)

        # title, created, language, description, available, license, accessRights

        computeFromExistingFields(jobId, False)
        r.refresh_from_db()

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

        jobId = initDummyTransfer(reportData=report, pageData=[__TEST_PAGES__[0]])
        r = Report.objects.get(job=jobId)

        # title, created, language, description, available, license, accessRights

        computeFromExistingFields(jobId, False)
        r.refresh_from_db()

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
        r = Report.objects.get(job=jobId)

        # title, created, language, description, available, license, accessRights

        computeFromExistingFields(jobId, False)
        r.refresh_from_db()

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

        step = ProcessingStep.objects.get(job_id=jobId, processingStepType=ProcessingStep.ProcessingStepType.GENERATE)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("language", step.log)

    def test_emptyLicense(self):
        initDefaultValues({"license": "", "language": "test"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId, processingStepType=ProcessingStep.ProcessingStepType.GENERATE)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("license", step.log)

    def test_noLicense(self):
        initDefaultValues({"language": "test"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId, processingStepType=ProcessingStep.ProcessingStepType.GENERATE)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("license", step.log)

    def test_noYearOffset(self):
        initDefaultValues({"language": "test", "license": "license"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId, processingStepType=ProcessingStep.ProcessingStepType.GENERATE)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("offset", step.log)

    def test_negativeYearOffset(self):
        initDefaultValues({"yearOffset": -1, "language": "test", "license": "license"})
        initDummyFilemaker()
        jobId = initDummyTransfer()

        computeFromExistingFields(jobId, False)

        step = ProcessingStep.objects.get(job_id=jobId, processingStepType=ProcessingStep.ProcessingStepType.GENERATE)
        self.assertEqual(step.status, Status.ERROR)
        self.assertIn("offset is negative", step.log)
