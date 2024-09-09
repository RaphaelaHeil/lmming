from datetime import date, datetime

import pandas as pd
from django.test import TestCase

from metadata.models import Report, ExtractionTransfer, Job, ProcessingStep, Status, ExternalRecord
from metadata.utils import parseFilename, buildReportIdentifier, buildProcessingSteps, updateExternalRecords


class ParseFilenameTests(TestCase):

    def test_singleYearNoPage(self):
        results = parseFilename("fac_01234_arsberattelse_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234",
                              "page": 1})

    def test_leadingDigits(self):
        results = parseFilename("0123_fac_01234_arsberattelse_1919_sid-01.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1919, 1, 1)],
                              "union_id": "1234",
                              "page": 1})

    def test_multiYearHyphenNoPage(self):
        results = parseFilename("0123_fac_01234_arsberattelse_1919-1920.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT,
                              "date": [datetime(1919, 1, 1), datetime(1920, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_multiYearUnderscore(self):
        results = parseFilename("0123_fac_01234_arsberattelse_1919_1920.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT,
                              "date": [datetime(1919, 1, 1), datetime(1920, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_multiYearOch(self):
        results = parseFilename("fac_00178_revisionsberattelse_1922 och 1923_sid-01")
        self.assertDictEqual(results, {"type": Report.DocumentType.FINANCIAL_STATEMENT,
                                       "date": [datetime(1922, 1, 1), datetime(1923, 1, 1)], "union_id": "178",
                                       "page": 1})

    def test_missingUnionId(self):
        self.assertRaises(SyntaxError, parseFilename, "fac_revisionsberattelse_1922 och 1923_sid-01")

    def test_missingYearNoPageIdentifier(self):
        self.assertRaises(SyntaxError, parseFilename, "fac_01234_revisionsberattelse_01")

    def test_missingYearNoPage(self):
        self.assertRaises(SyntaxError, parseFilename, "fac_01234_revisionsberattelse")

    def test_missingYearWithPageIdentifier(self):
        self.assertRaises(SyntaxError, parseFilename, "fac_01234_revisionsberattelse_sid-01")

    def test_missingReportType(self):
        self.assertRaises(SyntaxError, parseFilename, "fac_01234_1922 och 1923_sid-01")

    def test_arsberattelseCaptialised(self):
        results = parseFilename("fac_01234_ARSBERATTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_arsberattelseWithCaptialisedUmlaut(self):
        results = parseFilename("fac_01234_ARSBERÄTTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_arsberattelseWithCaptialisedOverring(self):
        results = parseFilename("fac_01234_ÅRSBERATTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_arsberattelseWithUmlaut(self):
        results = parseFilename("fac_01234_arsberättelse_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_arsberattelseWithOverring(self):
        results = parseFilename("fac_01234_årsberattelse_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_verksamhetsberattelseCapitalised(self):
        results = parseFilename("fac_01234_VERKSAMHETSBERATTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_verksamhetsberattelseWithUmlaut(self):
        results = parseFilename("fac_01234_verksamhetsberättelse_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_verksamhetsberattelseWithCapitalisedUmlaut(self):
        results = parseFilename("fac_01234_VERKSAMHETSBERÄTTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_revisionsberattelseCapitalised(self):
        results = parseFilename("fac_01234_REVISIONSBERATTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_revisionsberattelseWithCapitalisedUmlaut(self):
        results = parseFilename("fac_01234_REVISIONSBERÄTTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_funkyPageNumber(self):
        results = parseFilename("fac_01234_arsberattelse_1910_sid-001_01.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1910, 1, 1)],
                              "union_id": "1234", "page": 1})

    def test_fullStartDate(self):
        results = parseFilename("arab_01281_revisionsberattelse_1902-03-31--1903_sid-0001.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT,
                              "date": [datetime(1902, 3, 31), datetime(1903, 1, 1)], "union_id": "1281", "page": 1})

    def test_fullEndDate(self):
        results = parseFilename("arab_01281_revisionsberattelse_1901--1902-03-31_sid-0001.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT,
                              "date": [datetime(1901, 1, 1), datetime(1902, 3, 31)], "union_id": "1281", "page": 1})

    def test_fullDates(self):
        results = parseFilename("arab_01281_revisionsberattelse_1902-02-02--1902-03-31_sid-0001.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT,
                              "date": [datetime(1902, 2, 2), datetime(1902, 3, 31)], "union_id": "1281", "page": 1})

    def test_bilaga(self):
        results = parseFilename("arab_00550_verksamhetsberattelse_1980_bilaga_sid-0001.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [datetime(1980, 1, 1)],
                              "union_id": "550", "page": 1})


class BuildReportIdentifierTests(TestCase):

    def test_annualReportSingleYear(self):
        a = {"type": Report.DocumentType.ANNUAL_REPORT, "date": [date(1910, 1, 1)], "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-1910-01-01", buildReportIdentifier(a))

    def test_annualReportDoubleYear(self):
        a = {"type": Report.DocumentType.ANNUAL_REPORT, "date": [date(1910, 1, 1), date(1911, 1, 1)],
             "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-1910-01-01--1911-01-01", buildReportIdentifier(a))

    def test_financialStatementSingleYear(self):
        a = {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": [date(1910, 1, 1)], "union_id": "1234", "page": 1}
        self.assertEquals("1234-FINANCIAL_STATEMENT-1910-01-01", buildReportIdentifier(a))

    def test_financialStatementDoubleYear(self):
        a = {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": [date(1910, 1, 1), date(1911, 1, 1)],
             "union_id": "1234", "page": 1}
        self.assertEquals("1234-FINANCIAL_STATEMENT-1910-01-01--1911-01-01", buildReportIdentifier(a))

    def test_multiTypeSingleYear(self):
        a = {"type": [Report.DocumentType.ANNUAL_REPORT, Report.DocumentType.FINANCIAL_STATEMENT],
             "date": [date(1910, 1, 1)],
             "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-FINANCIAL_STATEMENT-1910-01-01", buildReportIdentifier(a))

    def test_multiTypeDoubleYear(self):
        a = {"type": [Report.DocumentType.ANNUAL_REPORT, Report.DocumentType.FINANCIAL_STATEMENT],
             "date": [date(1910, 1, 1), date(1911, 1, 1)], "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-FINANCIAL_STATEMENT-1910-01-01--1911-01-01", buildReportIdentifier(a))


class BuildProcessingStepsTests(TestCase):

    def test_buildFacSteps(self):
        et = ExtractionTransfer.objects.create(name="TestTransfer")

        report = Report.objects.create(transfer=et, unionId="2")
        job = Job.objects.create(transfer=et, report=report)
        report.job = job
        report.save()

        config = [{"stepType": ProcessingStep.ProcessingStepType.FILENAME,
                   "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False},
                  {"stepType": ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP,
                   "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False},
                  {"stepType": ProcessingStep.ProcessingStepType.GENERATE,
                   "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False},
                  {"stepType": ProcessingStep.ProcessingStepType.FAC_MANUAL,
                   "mode": ProcessingStep.ProcessingStepMode.MANUAL, "humanValidation": True},
                  {"stepType": ProcessingStep.ProcessingStepType.NER,
                   "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False},
                  {"stepType": ProcessingStep.ProcessingStepType.MINT_ARKS,
                   "mode": ProcessingStep.ProcessingStepMode.AUTOMATIC, "humanValidation": False}
                  ]

        buildProcessingSteps(config, job)

        steps = ProcessingStep.objects.filter(job=job).order_by("order")

        expected = [
            (ProcessingStep.ProcessingStepType.FILENAME, ProcessingStep.ProcessingStepMode.AUTOMATIC.value, False),
            (ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP, ProcessingStep.ProcessingStepMode.AUTOMATIC.value,
             False),
            (ProcessingStep.ProcessingStepType.GENERATE, ProcessingStep.ProcessingStepMode.AUTOMATIC.value, False),
            (ProcessingStep.ProcessingStepType.FAC_MANUAL, ProcessingStep.ProcessingStepMode.MANUAL.value, True),
            (ProcessingStep.ProcessingStepType.NER, ProcessingStep.ProcessingStepMode.AUTOMATIC.value, False),
            (ProcessingStep.ProcessingStepType.MINT_ARKS, ProcessingStep.ProcessingStepMode.AUTOMATIC.value, False)
        ]

        self.assertEqual(len(expected), len(steps))

        for step, exp in zip(steps, expected):
            self.assertEqual(exp[0].order, step.order)
            self.assertEqual(exp[0].value, step.processingStepType)
            self.assertEqual(Status.PENDING, step.status)
            self.assertEqual(exp[1], step.mode)
            self.assertEqual(exp[2], step.humanValidation)

    def test_noJob(self):
        config = {"filenameMode": "AUTOMATIC", "filenameHumVal": False, }
        self.assertRaises(TypeError, buildProcessingSteps, config, None)

    def test_noConfig(self):
        et = ExtractionTransfer.objects.create(name="TestTransfer")

        report = Report.objects.create(transfer=et, unionId="2")
        job = Job.objects.create(transfer=et, report=report)
        report.job = job
        report.save()

        self.assertRaises(TypeError, buildProcessingSteps, None, job)

    def test_emptyConfig(self):
        et = ExtractionTransfer.objects.create(name="TestTransfer")

        report = Report.objects.create(transfer=et, unionId="2")
        job = Job.objects.create(transfer=et, report=report)
        report.job = job
        report.save()

        self.assertRaises(TypeError, buildProcessingSteps, [], job)


class UpdateExternalRecordsTests(TestCase):

    def test_update(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "org": "1O", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "2A", "org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(2, len(externalRecords))
            self.assertEqual(externalRecords[0].archiveId, "1A")
            self.assertEqual(externalRecords[1].archiveId, "2A")

    def test_ArchiveIdColumnMissing(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"org": "1O", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            with self.assertRaises(ValueError) as cm:
                updateExternalRecords(df)
            self.assertIn("archive", cm.exception.args[0])

    def test_OrganisationNameColumnMissing(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "2A", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            with self.assertRaises(ValueError) as cm:
                updateExternalRecords(df)
            self.assertIn("org", cm.exception.args[0])

    def test_ArabCoverageColumnMissing(self):
        with self.settings(ARCHIVE_INST="ARAB", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "org": "1O", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L"},
                                            {"archive": "2A", "org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(2, len(externalRecords))
            self.assertEqual(externalRecords[0].archiveId, "1A")
            self.assertEqual(externalRecords[1].archiveId, "2A")

    def test_FacCoverageColumnMissing(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "org": "1O", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L"},
                                            {"archive": "2A", "org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(2, len(externalRecords))
            self.assertEqual(externalRecords[0].archiveId, "1A")
            self.assertEqual(externalRecords[1].archiveId, "2A")

    def test_OptionalColumnMissing(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "org": "1O", "county": "1C", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "2A", "org": "2O", "county": "2C", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(2, len(externalRecords))
            self.assertEqual(externalRecords[0].archiveId, "1A")
            self.assertEqual(externalRecords[1].archiveId, "2A")

    def test_ArchiveIdColumnEmpty(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "", "org": "1O", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "", "org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(0, len(externalRecords))

    def test_OrganisationNameColumnEmpty(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "org": "", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "2A", "org": "", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(0, len(externalRecords))

    def test_ArchiveIdColumnPartiallyEmpty(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "", "org": "1O", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "2A", "org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(1, len(externalRecords))
            self.assertEqual("2A", externalRecords[0].archiveId)

    def test_OrganisationNameColumnPartiallyEmpty(self):
        with self.settings(ARCHIVE_INST="FAC", ER_ARCHIVE_ID="archive", ER_ORGANISATION_NAME="org", ER_COUNTY="county",
                           ER_MUNICIPALITY="muni", ER_CITY="city", ER_PARISH="parish", ER_CATALOGUE_LINK="link",
                           ER_COVERAGE="cov"):
            df = pd.DataFrame.from_records([{"archive": "1A", "org": "", "county": "1C", "muni": "1M", "city": "1CI",
                                             "parish": "1P", "link": "1L", "cov": "1CO"},
                                            {"archive": "2A", "org": "2O", "county": "2C", "muni": "2M", "city": "2CI",
                                             "parish": "2P", "link": "2L", "cov": "2CO"}])
            updateExternalRecords(df)
            externalRecords = ExternalRecord.objects.all()
            self.assertEqual(1, len(externalRecords))
            self.assertEqual("2A", externalRecords[0].archiveId)
