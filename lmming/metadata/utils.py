import io
import re
import zipfile
from typing import Dict, Union, List, Any

import pandas as pd

from lmming import settings
from metadata.models import Report, ExtractionTransfer, FilemakerEntry

__REPORT_TYPE_INDEX__ = {"arsberattelse": Report.DocumentType.ANNUAL_REPORT,
                         "verksamhetsberattelse": Report.DocumentType.ANNUAL_REPORT,
                         "revisionsberattelse": Report.DocumentType.FINANCIAL_STATEMENT}


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


def buildTransferCsvs(transfer: ExtractionTransfer):
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

        for page in report.page_set.all().order_by("order"):
            pageSummary.append({"dcterms:isPartOf": report.identifier,
                                "dcterms:identifier": 0,
                                # TODO: build from report base # TODO: requires changes in Archival .... :S
                                # TODO: image naming needs to be pre-determined and cannot depend on Archivematica >.<
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

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("items.csv", pd.DataFrame.from_records(reportSummary).to_csv(index=False))
        zf.writestr("media.csv", pd.DataFrame.from_records(pageSummary).to_csv(index=False))
    zip_buffer.seek(0)

    return zip_buffer


def updateFilemakerData(df: pd.DataFrame):
    FilemakerEntry.objects.all().delete()
    df = df.fillna("")
    keys = settings.FILEMAKER_SETTINGS
    for idx, row in df.iterrows():
        if row[keys.archiveId] and row[keys.organisationName]:
            FilemakerEntry.objects.create(archiveId=row[keys.archiveId], organisationName=row[keys.organisationName],
                                          county=row[keys.county], municipality=row[keys.municipality],
                                          city=row[keys.city], parish=row[keys.parish])
        else:
            continue  # TODO: add logging about skipping an entry!
