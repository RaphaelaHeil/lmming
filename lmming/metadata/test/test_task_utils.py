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

    def test_distrikt(self):
        level = getFacCoverage("this is a distrikt name")
        self.assertEqual(Report.UnionLevel.DISTRICT, level)

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

    def test_emptyCoverage(self):
        level = getArabCoverage("")
        self.assertEqual(Report.UnionLevel.OTHER, level)

    def test_unknownCoverage(self):
        level = getArabCoverage("asjdnkajsn")
        self.assertEqual(Report.UnionLevel.OTHER, level)

    def test_workplace(self):
        level = getArabCoverage("workplace")
        self.assertEqual(Report.UnionLevel.WORKPLACE, level)

    def test_section(self):
        level = getArabCoverage("section")
        self.assertEqual(Report.UnionLevel.SECTION, level)

    def test_division(self):
        level = getArabCoverage("division")
        self.assertEqual(Report.UnionLevel.DIVISION, level)

    def test_district(self):
        level = getArabCoverage("district")
        self.assertEqual(Report.UnionLevel.DISTRICT, level)

    def test_nationalBranch(self):
        level = getArabCoverage("national branch")
        self.assertEqual(Report.UnionLevel.NATIONAL_BRANCH, level)

    def test_nationalFederation(self):
        level = getArabCoverage("national federation")
        self.assertEqual(Report.UnionLevel.NATIONAL_FEDERATION, level)

    def test_internationalBranch(self):
        level = getArabCoverage("international branch")
        self.assertEqual(Report.UnionLevel.INTERNATIONAL_BRANCH, level)

    def test_internationalFederation(self):
        level = getArabCoverage("international federation")
        self.assertEqual(Report.UnionLevel.INTERNATIONAL_FEDERATION, level)

    def test_other(self):
        level = getArabCoverage("other")
        self.assertEqual(Report.UnionLevel.OTHER, level)


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

    def test_createArabTitle(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991", title)

    def test_duplicateYear(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1991, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991", title)

    def test_consecutiveYears(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1992, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991 -- 1992", title)

    def test_nonConsecutiveYears(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1993, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991, 1993", title)

    def test_singleThenConsecutiveYears(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1993, 1, 1), date(1994, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991, 1993 -- 1994", title)

    def test_consecutiveThenSingleYear(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1992, 1, 1), date(1995, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991 -- 1992, 1995", title)

    def test_multipleSingleThenConsecutiveYear(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1989, 1, 1), date(1993, 1, 1), date(1994, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1989, 1991, 1993 -- 1994", title)

    def test_consecutiveThenMultipleSingle(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1992, 1, 1), date(1995, 1, 1), date(1997, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991 -- 1992, 1995, 1997", title)

    def test_multipleConsecutiveYears(self):
        unionName = "Union X"
        dates = [date(1991, 1, 1), date(1992, 1, 1), date(1994, 1, 1), date(1995, 1, 1)]
        title = createArabTitle(unionName, dates)
        self.assertEqual("Union X 1991 -- 1992, 1994 -- 1995", title)

    def test_unionNameEmpty(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle("", [date(1991, 1, 1)])
        self.assertIn("no union name was supplied", str(cm.exception))

    def test_unionNameNone(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle(None, [date(1991, 1, 1)])
        self.assertIn("no union name was supplied", str(cm.exception))

    def test_yearsEmpty(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle("Union X", [])
        self.assertIn("no dates were supplied", str(cm.exception))

    def test_yearsNone(self):
        with self.assertRaises(TypeError) as cm:
            createArabTitle("Union X", None)
        self.assertIn("no dates were supplied", str(cm.exception))
