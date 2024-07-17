import re
import zipfile
from datetime import date
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Dict, Union, List, Any, Tuple
from requests.compat import urljoin

import pandas as pd
from lxml.etree import SubElement, register_namespace, QName, Element, tostring

from lmming import settings
from metadata.models import Report, ExtractionTransfer, ExternalRecord

__REPORT_TYPE_INDEX__ = {"arsberattelse": Report.DocumentType.ANNUAL_REPORT,
                         "verksamhetsberattelse": Report.DocumentType.ANNUAL_REPORT,
                         "revisionsberattelse": Report.DocumentType.FINANCIAL_STATEMENT}

__DUMMY_DIR__ = Path(__file__).parent.resolve() / "dummy_content"


def parseFilename(filename: str) -> Dict[str, Union[int, str, List[str]]]:
    """
    Retrieves the union's ID, a type hint for the report type, the report's year(s) and the page number from the given
    filename.

    :param filename: filename to be parsed - may include *.xml or *.txt extensions
    :return: dictionary, containing the ``union_id``, report ``type`` hint, one or more ``date`` and the ``page`` number
    :raises SyntaxError: if the filename is not formatted according to the project's standards
    """

    if filename.endswith(".xml") or filename.endswith(".txt"):
        filename = filename[:-4]

    if "fac" in filename:
        filename = filename[filename.index("fac") + 4:]
    if "arab" in filename:
        filename = filename[filename.index("arab") + 5:]

    if "sid" in filename:
        matches = re.findall(r"(?<=sid-)\d*", filename)
        page = int(matches[0])
        filename = filename.split("sid")[0][:-1]
    else:
        m = re.findall(r"(?<=1[89]\d{2}[_-])\d*", filename)
        if m:
            val = m[-1]
            if not re.match(r"1[89]\d{2}", val):
                page = int(val)
                idx = filename.rfind(val)
                filename = filename[:idx]
            else:
                page = 1
        else:
            page = 1

    s = filename.split("_")
    if len(s) < 3:
        raise SyntaxError(
            "The provided filename does not follow one of the expected patterns. Could not identify one or more of the "
            "following: union identifier, report type, report year(s)")

    unionId = s[0].lstrip("0") or "0"

    typeName = s[1]
    typeName = typeName.lower()
    typeName = typeName.replace("ä", "a")
    typeName = typeName.replace("å", "a")
    typeName = typeName.replace("ö", "o")
    if typeName in __REPORT_TYPE_INDEX__:
        reportType = __REPORT_TYPE_INDEX__[typeName]
    else:
        reportType = Report.DocumentType.ANNUAL_REPORT

    dates = []
    d = " ".join(s[2:])  # in case two years were separated by underscores
    ma = re.findall(r"1[89]\d{2}", d)
    if ma:
        for m in ma:
            dates.append(int(m))
    if len(dates) == 1:
        dates = int(dates[0])
    if not dates:
        raise SyntaxError(
            "The provided filename does not follow one of the expected patterns. Could not identify one or more of the "
            "following: union identifier, report type, report year(s)")

    return {"date": dates, "union_id": unionId, "type": reportType, "page": page}


def buildReportIdentifier(data: Dict[str, Union[str, int, List[str]]]) -> str:
    date = data["date"]
    if isinstance(date, list):
        date = "-".join([str(d) for d in sorted(date)])

    reportType = data["type"]
    if isinstance(reportType, list):
        reportType = "-".join(sorted(reportType))

    return f"{data['union_id']}-{reportType}-{date}"


def __toOmekaList__(ll: List[Any]) -> str:
    if ll:
        return " | ".join(str(e) for e in ll)
    else:
        return ""


def __toCSList__(ll: List[Any]) -> str:
    if ll:
        return ",".join(str(e) for e in ll)
    else:
        return ""


def __isRestricted__(availableDate) -> bool:
    return availableDate > date.today()


def __buildOmekaSummaries__(transfer: ExtractionTransfer, checkRestriction: bool = False) -> Tuple[
    List[Dict[str, str]], List[Dict[str, str]]]:
    reportSummary = []
    pageSummary = []
    for report in transfer.report_set.all():
        # TODO: add null/none checks!!
        reportSummary.append({"dcterms:identifier": report.identifier,
                              "dcterms:title": report.title,
                              "dcterms:creator": report.creator,
                              "dcterms:date": "/".join([str(d.year) for d in report.date]),
                              "dcterms:coverage": Report.UnionLevel[report.coverage].label,
                              "dcterms:language": __toOmekaList__(report.language),
                              "dcterms:spatial": __toOmekaList__(report.spatial),
                              "dcterms:type": __toOmekaList__([Report.DocumentType[x].label for x in report.type]),
                              "dcterms:license": __toOmekaList__(report.license),
                              "dcterms:isVersionOf": report.isVersionOf,
                              "dcterms:isFormatOf": __toOmekaList__(
                                  [Report.DocumentFormat[x].label for x in report.isFormatOf]),
                              "dcterms:accessRights": Report.AccessRights[report.accessRights].label,
                              "dcterms:relation": __toOmekaList__(report.relation),
                              "dcterms:created": report.created.year,
                              "dcterms:available": report.available,
                              "dcterms:source": __toOmekaList__(report.source),
                              "dcterms:description": report.description})

        if checkRestriction and __isRestricted__(report.available):
            pageSummary.append({"dcterms:isPartOf": report.identifier,
                                "dcterms:identifier": urljoin(settings.IIIF_BASE_URL,
                                                              f"iiif/image/{report.noid}_1/info.json"),
                                "lm:transcription": "FOLKRÖRELSEARKVET FÖR UPPSALA LÄN The contents of this report are "
                                                    "not publicly available. Please contact Folkrörelsearkivet för "
                                                    "Uppsala Län for more information. Email: info@fauppsala.se "
                                                    "https://www.fauppsala.se/kontakt/ FOLKRÖRELSEARKIVET FÖR UPPSALA "
                                                    "LÄN", "lm:normalised": "", "lm:person": "", "lm:organisation": "",
                                "lm:location": "", "lm:time": "", "lm:work": "", "lm:event": "", "lm:object": "",
                                "lm:measure": False})
        else:
            for page in report.page_set.all().order_by("order"):
                pageSummary.append({"dcterms:isPartOf": report.identifier,
                                    "dcterms:identifier": page.identifier,
                                    "lm:transcription": page.transcription,
                                    "lm:normalised": page.normalisedTranscription,
                                    "lm:person": __toOmekaList__(page.persons),
                                    "lm:organisation": __toOmekaList__(page.organisations),
                                    "lm:location": __toOmekaList__(page.locations),
                                    "lm:time": __toOmekaList__(page.times),
                                    "lm:work": __toOmekaList__(page.works),
                                    "lm:event": __toOmekaList__(page.events),
                                    "lm:object": __toOmekaList__(page.ner_objects),
                                    "lm:measure": page.measures})

    return reportSummary, pageSummary


def buildTransferCsvs(transfer: ExtractionTransfer, checkRestriction: bool = False):
    reportSummary, pageSummary = __buildOmekaSummaries__(transfer, checkRestriction)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("items.csv", pd.DataFrame.from_records(reportSummary).to_csv(index=False))
        zf.writestr("media.csv", pd.DataFrame.from_records(pageSummary).to_csv(index=False))
    zip_buffer.seek(0)

    return zip_buffer


def buildStructMap(transfer: ExtractionTransfer, checkRestriction: bool = False) -> str:
    METS = "http://www.loc.gov/METS/"
    register_namespace("mets", METS)
    f = partial(QName, METS)

    root = Element(f("mets"))
    structMap = SubElement(root, f("structMap"), TYPE="logical", ID="structMap_lm", LABEL="LM structure")
    outerDiv = SubElement(structMap, f("div"))

    for report in transfer.report_set.all():
        reportNode = SubElement(outerDiv, f("div"), TYPE="report", LABEL=report.title, ID=str(report.noid))

        if checkRestriction and __isRestricted__(report.available):
            filename = f"page_not_available_{report.noid}"
            pageNode = SubElement(reportNode, f("div"), TYPE="page", ORDER="1", LABEL=filename, ID=f"{report.noid}_1")
            SubElement(pageNode, f("fptr"), FILEID=f"{filename}.jpg", CONTENTIDS=f"objects/{filename}.jpg")
            SubElement(pageNode, f("fptr"), FILEID=f"{filename}.xml",
                       CONTENTIDS=f"objects/transcription/{filename}.xml")
        else:
            for page in report.page_set.all():
                pageNode = SubElement(reportNode, f("div"), TYPE="page", ORDER=str(page.order),
                                      LABEL=page.originalFileName, ID=f"{report.noid}_{page.order}")
                filename = Path(page.originalFileName).stem
                SubElement(pageNode, f("fptr"), FILEID=f"{filename}.jpg", CONTENTIDS=f"objects/{filename}.jpg")
                SubElement(pageNode, f("fptr"), FILEID=f"{filename}.xml",
                           CONTENTIDS=f"objects/transcription/{filename}.xml")

    return tostring(root, pretty_print=True, encoding="utf-8").decode("utf-8")


def buildNormalizationCsv(srcNames) -> str:
    data = []
    for f in srcNames:
        if f.endswith(".jpg"):
            data.append((f, f"manualNormalization/access/{f}", f"manualNormalization/preservation/{f[:-4]}.tif"))
        else:
            data.append((f"transcription/{f}", "", ""))
    df = pd.DataFrame.from_records(data)
    return df.to_csv(header=False, index=False)


def buildMetadataCsv(transfer: ExtractionTransfer, checkRestriction: bool = False) -> str:
    DC_FIELDS = ["dc.identifier", "dc.type", "dc.date", "dc.rights", "dc.description", "dc.language", "dc.coverage",
                 "dc.title", "dc.subject", "dc.creator", "dc.contributor", "dc.publisher", "dc.source", "dc.format",
                 "dc.relation"]  # extent and format
    records = []

    for report in transfer.report_set.all():
        if checkRestriction and __isRestricted__(report.available):
            row = {"dc.identifier": report.noid,
                   "dc.type": __toCSList__([Report.DocumentType[x].label for x in report.type]),
                   "dc.date": "/".join([str(d.year) for d in report.date]),
                   "dc.language": __toCSList__(report.language),
                   "dc.coverage": Report.UnionLevel[report.coverage].label,
                   "dc.title": report.title,
                   "dc.creator": report.creator,
                   "dc.source": __toCSList__(report.source),

                   "dc.relation": __toCSList__(report.relation),
                   "dc.format": f"{report.description} - {__toCSList__([Report.DocumentFormat[x].label for x in report.isFormatOf])}",
                   # "dc.description": report.description, # TODO: ???
                   "dc.rights1": Report.AccessRights[report.accessRights].label,
                   "dc.rights2": __toOmekaList__(report.license),
                   "dc.contributor": "", "dc.publisher": "", "dc.subject": ""  # these 3 stay emtpy for now!
                   }
            filename = f"page_not_available_{report.noid}"
            transcriptionFilename = f"objects/transcription/{filename}.xml"
            preserverationFilename = f"objects/{filename}.jpg"
            a = {"filename": transcriptionFilename}
            a.update(row)
            b = {"filename": preserverationFilename}
            b.update(row)
            records.append(a)
            records.append(b)
        else:
            row = {"dc.identifier": report.noid,
                   "dc.type": __toCSList__([Report.DocumentType[x].label for x in report.type]),
                   "dc.date": "/".join([str(d.year) for d in report.date]),
                   "dc.language": __toCSList__(report.language),
                   "dc.coverage": Report.UnionLevel[report.coverage].label,
                   "dc.title": report.title,
                   "dc.creator": report.creator,
                   "dc.source": __toCSList__(report.source),

                   "dc.relation": __toCSList__(report.relation),
                   "dc.format": f"{report.description} - {__toCSList__([Report.DocumentFormat[x].label for x in report.isFormatOf])}",
                   # "dc.description": report.description, # TODO: ???
                   "dc.rights1": Report.AccessRights[report.accessRights].label,
                   "dc.rights2": __toOmekaList__(report.license),
                   "dc.contributor": "", "dc.publisher": "", "dc.subject": ""  # these 3 stay emtpy for now!
                   }
            for page in report.page_set.all():
                transcriptionFilename = f"objects/transcription/{page.originalFileName}"
                preserverationFilename = f"objects/{page.originalFileName[:-4]}.jpg"
                a = {"filename": transcriptionFilename}
                a.update(row)
                b = {"filename": preserverationFilename}
                b.update(row)
                records.append(a)
                records.append(b)
    df = pd.DataFrame.from_records(records)
    cols = df.columns.to_list()
    cols[cols.index("dc.rights1")] = "dc.rights"
    cols[cols.index("dc.rights2")] = "dc.rights"
    print(cols)
    return df.to_csv(index=False, header=cols)


def buildFolderStructure(transfer: ExtractionTransfer, checkRestriction: bool = False):
    outfile = BytesIO()
    filenames = []

    with zipfile.ZipFile(outfile, 'w', zipfile.ZIP_DEFLATED) as zf:
        zif = zipfile.ZipInfo("manualNormalization/access/")
        zf.writestr(zif, "")
        zif = zipfile.ZipInfo("manualNormalization/preservation/")
        zf.writestr(zif, "")

        for report in transfer.report_set.all():
            if checkRestriction and __isRestricted__(report.available):
                page_name = f"page_not_available_{report.noid}"
                zf.write(__DUMMY_DIR__ / "page_not_available.jpg", f"manualNormalization/access/{page_name}.jpg")
                zf.write(__DUMMY_DIR__ / "page_not_available.jpg", f"{page_name}.jpg")

                filenames.append(f"{page_name}.tif")
                zf.write(__DUMMY_DIR__ / "page_not_available.tif", f"manualNormalization/preservation/{page_name}.tif")

                filenames.append(f"{page_name}.xml")

                zf.write(__DUMMY_DIR__ / "page_not_available.xml", f"transcription/{page_name}.xml")
            else:
                for page in report.page_set.all():
                    pageFileName = page.originalFileName
                    filenames.append(pageFileName)
                    filenames.append(str(Path(pageFileName).with_suffix(".jpg")))
                    zf.write(page.transcriptionFile.path, f"transcription/{pageFileName}")

        filenames.sort(key=lambda x: (x[-3:], x[:-4]))

        zf.writestr("manualNormalization/normalization.csv", buildNormalizationCsv(filenames))

        zf.writestr("metadata/metadata.csv", buildMetadataCsv(transfer, checkRestriction))
        zf.writestr("metadata/mets_structmap.xml", buildStructMap(transfer, checkRestriction))

        reportSummary, pageSummary = __buildOmekaSummaries__(transfer, checkRestriction)
        zf.writestr("items.csv", pd.DataFrame.from_records(reportSummary).to_csv(index=False))
        zf.writestr("media.csv", pd.DataFrame.from_records(pageSummary).to_csv(index=False))

        zf.close()
    outfile.seek(0)

    return outfile


def updateExternalRecords(df: pd.DataFrame):
    df = df.fillna("")

    ExternalRecord.objects.bulk_create([ExternalRecord(archiveId=row[settings.ER_ARCHIVE_ID],
                                                       organisationName=row[settings.ER_ORGANISATION_NAME],
                                                       county=row[settings.ER_COUNTY],
                                                       municipality=row[settings.ER_MUNICIPALITY],
                                                       city=row[settings.ER_CITY], parish=row[settings.ER_PARISH],
                                                       catalogueLink=row[settings.ER_CATALOGUE_LINK]) for _, row in
                                        df.iterrows()
                                        if row[settings.ER_ARCHIVE_ID] and row[settings.ER_ORGANISATION_NAME]],
                                       update_conflicts=True, unique_fields=["archiveId"],
                                       update_fields=["organisationName", "county", "municipality", "city",
                                                      "catalogueLink"],
                                       )
