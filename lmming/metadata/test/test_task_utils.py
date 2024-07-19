from django.test import TestCase

from metadata.models import Report
from metadata.task_utils import getArabCoverage, getFacCoverage, splitIfNotNone


class FacCoverageTests(TestCase):

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
