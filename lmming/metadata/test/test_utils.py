from django.test import TestCase
from metadata.utils import parseFilename, buildReportIdentifier
from metadata.models import Report, ExtractionTransfer
from datetime import date


class ParseFilenameTests(TestCase):

    def test_singleYearNoPage(self):
        results = parseFilename("fac_01234_arsberattelse_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_leadingDigits(self):
        results = parseFilename("0123_fac_01234_arsberattelse_1919_sid-01.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1919, "union_id": "1234",
                                       "page": 1})

    def test_multiYearHyphenNoPage(self):
        results = parseFilename("0123_fac_01234_arsberattelse_1919-1920.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [1919, 1920], "union_id": "1234",
                              "page": 1})

    def test_multiYearUnderscore(self):
        results = parseFilename("0123_fac_01234_arsberattelse_1919_1920.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.ANNUAL_REPORT, "date": [1919, 1920], "union_id": "1234",
                              "page": 1})

    def test_multiYearOch(self):
        results = parseFilename("fac_00178_revisionsberattelse_1922 och 1923_sid-01")
        self.assertDictEqual(results, {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": [1922, 1923],
                                       "union_id": "178", "page": 1})

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
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_arsberattelseWithCaptialisedUmlaut(self):
        results = parseFilename("fac_01234_ARSBERÄTTELSE_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_arsberattelseWithCaptialisedOverring(self):
        results = parseFilename("fac_01234_ÅRSBERATTELSE_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_arsberattelseWithUmlaut(self):
        results = parseFilename("fac_01234_arsberättelse_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_arsberattelseWithOverring(self):
        results = parseFilename("fac_01234_årsberattelse_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_verksamhetsberattelseCapitalised(self):
        results = parseFilename("fac_01234_VERKSAMHETSBERATTELSE_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_verksamhetsberattelseWithUmlaut(self):
        results = parseFilename("fac_01234_verksamhetsberättelse_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_verksamhetsberattelseWithCapitalisedUmlaut(self):
        results = parseFilename("fac_01234_VERKSAMHETSBERÄTTELSE_1910.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})

    def test_revisionsberattelseCapitalised(self):
        results = parseFilename("fac_01234_REVISIONSBERATTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": 1910, "union_id": "1234",
                              "page": 1})

    def test_revisionsberattelseWithCapitalisedUmlaut(self):
        results = parseFilename("fac_01234_REVISIONSBERÄTTELSE_1910.xml")
        self.assertDictEqual(results,
                             {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": 1910, "union_id": "1234",
                              "page": 1})

    def test_funkyPageNumber(self):
        results = parseFilename("fac_01234_arsberattelse_1910_sid-001_01.xml")
        self.assertDictEqual(results, {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234",
                                       "page": 1})


class BuildReportIdentifierTests(TestCase):

    def test_annualReportSingleYear(self):
        a = {"type": Report.DocumentType.ANNUAL_REPORT, "date": 1910, "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-1910", buildReportIdentifier(a))

    def test_annualReportDoubleYear(self):
        a = {"type": Report.DocumentType.ANNUAL_REPORT, "date": [1910, 1911], "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-1910-1911", buildReportIdentifier(a))

    def test_financialStatementSingleYear(self):
        a = {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": 1910, "union_id": "1234", "page": 1}
        self.assertEquals("1234-FINANCIAL_STATEMENT-1910", buildReportIdentifier(a))

    def test_financialStatementDoubleYear(self):
        a = {"type": Report.DocumentType.FINANCIAL_STATEMENT, "date": [1910, 1911], "union_id": "1234", "page": 1}
        self.assertEquals("1234-FINANCIAL_STATEMENT-1910-1911", buildReportIdentifier(a))

    def test_multiTypeSingleYear(self):
        a = {"type": [Report.DocumentType.ANNUAL_REPORT, Report.DocumentType.FINANCIAL_STATEMENT], "date": 1910,
             "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-FINANCIAL_STATEMENT-1910", buildReportIdentifier(a))

    def test_multiTypeDoubleYear(self):
        a = {"type": [Report.DocumentType.ANNUAL_REPORT, Report.DocumentType.FINANCIAL_STATEMENT],
             "date": [1910, 1911], "union_id": "1234", "page": 1}
        self.assertEquals("1234-ANNUAL_REPORT-FINANCIAL_STATEMENT-1910-1911", buildReportIdentifier(a))


class ReportCreationTests(TestCase):

    def test_reportCreation(self):
        reportType = [Report.DocumentType.ANNUAL_REPORT]
        dateList = [date(1910, 1, 1)]
        unionId = "1234"

        transferInstance = ExtractionTransfer.objects.create(name="lion")

        r = Report.objects.create(transfer=transferInstance, unionId=unionId, type=reportType, date=dateList)
