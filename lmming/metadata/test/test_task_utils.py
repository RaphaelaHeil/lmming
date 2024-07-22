from datetime import date
from unittest import expectedFailure

from django.test import TestCase

from metadata.models import Report
from metadata.tasks.utils import getArabCoverage, getFacCoverage, splitIfNotNone, createArabTitle


class FacCoverageTests(TestCase):

    @expectedFailure
    def test_multipleIndicators(self):
        level = getFacCoverage("this is sektion X, avdelning Y")
        # TODO: discuss plausible naming schemes and which are the correct responses
        self.assertEqual(Report.UnionLevel.DIVISION, level)

    def test_klubb(self):
        level = getFacCoverage("this is a klubb name")
        self.assertEqual(Report.UnionLevel.WORKPLACE, level)

    def test_sektion(self):
        level = getFacCoverage("this is a sektion name")
        self.assertEqual(Report.UnionLevel.SECTION, level)

    def test_avd(self):
        level = getFacCoverage("this is a avd name")
        self.assertEqual(Report.UnionLevel.DIVISION, level)

    def test_avdelning(self):
        level = getFacCoverage("this is a avdelning name")
        self.assertEqual(Report.UnionLevel.DIVISION, level)

    def test_noIndicator(self):
        level = getFacCoverage("asjdnkajsn")
        self.assertEqual(Report.UnionLevel.OTHER, level)

    def test_capitalKlubb(self):
        level = getFacCoverage("THIS IS A KLUBB NAME")
        self.assertEqual(Report.UnionLevel.WORKPLACE, level)

    def test_capitalSektion(self):
        level = getFacCoverage("THIS IS A SEKTION NAME")
        self.assertEqual(Report.UnionLevel.SECTION, level)

    def test_capitalAvd(self):
        level = getFacCoverage("THIS IS A AVD NAME")
        self.assertEqual(Report.UnionLevel.DIVISION, level)

    def test_capitalAvdelning(self):
        level = getFacCoverage("THIS IS A AVDELNING NAME")
        self.assertEqual(Report.UnionLevel.DIVISION, level)


class ArabCoverageTests(TestCase):

    def test_riks(self):
        level = getArabCoverage("this is a riks name")
        self.assertEqual(Report.UnionLevel.NATIONAL_BRANCH, level)

    def test_regional(self):
        level = getArabCoverage("this is a regional name")
        self.assertEqual(Report.UnionLevel.DISTRICT, level)

    def test_lokal(self):
        level = getArabCoverage("this is a lokal name")
        self.assertEqual(Report.UnionLevel.SECTION, level)

    def test_noIndicator(self):
        level = getArabCoverage("asjdnkajsn")
        self.assertEqual(Report.UnionLevel.OTHER, level)

    def test_capitalRiks(self):
        level = getArabCoverage("THIS IS A RIKS NAME")
        self.assertEqual(Report.UnionLevel.NATIONAL_BRANCH, level)

    def test_capitalRegional(self):
        level = getArabCoverage("THIS IS A REGIONAL NAME")
        self.assertEqual(Report.UnionLevel.DISTRICT, level)

    def test_capitalLokal(self):
        level = getArabCoverage("THIS IS A LOKAL NAME")
        self.assertEqual(Report.UnionLevel.SECTION, level)


class SplitIfNotNoneTests(TestCase):

    def test_csvString(self):
        split = splitIfNotNone("this,is,a,test")
        self.assertListEqual(["this", "is", "a", "test"], split)

    def test_csvStringWithSpaces(self):
        split = splitIfNotNone("this , is , a , test")
        self.assertListEqual(["this", "is", "a", "test"], split)

    def test_None(self):
        split = splitIfNotNone(None)
        self.assertListEqual([], split)

    def test_Empty(self):
        split = splitIfNotNone("")
        self.assertListEqual([], split)


class CreateArabTitleTests(TestCase):

    def test_annualReport(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991", title)

    def test_financialStatement(self):
        reportTypes = [Report.DocumentType.FINANCIAL_STATEMENT]
        dates = [date(1991, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Financial Statement 1991", title)

    def test_multipleReportTypes(self):
        reportTypes = [Report.DocumentType.FINANCIAL_STATEMENT, Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report, Financial Statement 1991", title)

    def test_duplicateReportTypes(self):
        reportTypes = [Report.DocumentType.FINANCIAL_STATEMENT, Report.DocumentType.FINANCIAL_STATEMENT]
        dates = [date(1991, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Financial Statement 1991", title)

    def test_duplicateYear(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1991, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991", title)

    def test_consecutiveYears(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1992, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991 -- 1992", title)

    def test_nonConsecutiveYears(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1993, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991, 1993", title)

    def test_singleThenConsecutiveYears(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1993, 1, 1), date(1994, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991, 1993 -- 1994", title)

    def test_consecutiveThenSingleYear(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1992, 1, 1), date(1995, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991 -- 1992, 1995", title)

    def test_multipleSingleThenConsecutiveYear(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1989, 1, 1), date(1993, 1, 1), date(1994, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1989, 1991, 1993 -- 1994", title)
        pass

    def test_consecutiveThenMultipleSingle(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1992, 1, 1), date(1995, 1, 1), date(1997, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991 -- 1992, 1995, 1997", title)

    def test_multipleConsecutiveYears(self):
        reportTypes = [Report.DocumentType.ANNUAL_REPORT]
        dates = [date(1991, 1, 1), date(1992, 1, 1), date(1994, 1, 1), date(1995, 1, 1)]
        title = createArabTitle(reportTypes, dates)
        self.assertEqual("Annual Report 1991 -- 1992, 1994 -- 1995", title)

    def test_reportTypesEmpty(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle([], [date(1991, 1, 1)])
        self.assertIn("no report types were supplied", str(cm.exception))

    def test_reportTypesNone(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle(None, [date(1991, 1, 1)])
        self.assertIn("no report types were supplied", str(cm.exception))

    def test_yearsEmpty(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle([Report.DocumentType.ANNUAL_REPORT], [])
        self.assertIn("no dates were supplied", str(cm.exception))

    def test_yearsNone(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle([Report.DocumentType.ANNUAL_REPORT], None)
        self.assertIn("no dates were supplied", str(cm.exception))

    def test_unknownReportType(self):
        with self.assertRaises(ValueError) as cm:
            createArabTitle([Report.DocumentType.ANNUAL_REPORT, "dummy"], [date(1991, 1, 1)])
        self.assertIn("unknown report type", str(cm.exception))
