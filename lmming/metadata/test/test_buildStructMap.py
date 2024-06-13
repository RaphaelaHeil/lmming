from django.test import TestCase

from metadata.models import ExtractionTransfer, Report, Page
from metadata.utils import buildStructMap


class BuildStructMapTests(TestCase):

    def setUp(self):
        et = ExtractionTransfer.objects.create(name="Test")

        r1 = Report.objects.create(transfer=et, title="Title", noid="test_noid")
        Page.objects.create(report=r1, order=1, originalFileName="file1.tif")
        Page.objects.create(report=r1, order=10, originalFileName="file10.xml")

    def test_buildSimpleStructMap(self):
        et = ExtractionTransfer.objects.all()[0]
        structMap = buildStructMap(et)

        ref = ('<mets:mets xmlns:mets="http://www.loc.gov/METS/">\n'
               '  <mets:structMap TYPE="logical" ID="structMap_lm" LABEL="LM structure">\n'
               '    <mets:div>\n'
               '      <mets:div TYPE="report" LABEL="Title" ID="test_noid">\n'
               '        <mets:div TYPE="page" ORDER="1" LABEL="file1.tif" ID="test_noid_1">\n'
               '          <mets:fptr FILEID="file1.tif" CONTENTIDS="objects/preservation/file1.tif"/>\n'
               '          <mets:fptr FILEID="file1.xml" CONTENTIDS="objects/transcription/file1.xml"/>\n'
               '        </mets:div>\n'
               '        <mets:div TYPE="page" ORDER="10" LABEL="file10.xml" ID="test_noid_10">\n'
               '          <mets:fptr FILEID="file10.tif" CONTENTIDS="objects/preservation/file10.tif"/>\n'
               '          <mets:fptr FILEID="file10.xml" CONTENTIDS="objects/transcription/file10.xml"/>\n'
               '        </mets:div>\n'
               '      </mets:div>\n'
               '    </mets:div>\n'
               '  </mets:structMap>\n'
               '</mets:mets>\n')
        self.assertEqual(structMap, ref)
