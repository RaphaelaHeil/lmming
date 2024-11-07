import re
import zipfile
from datetime import datetime
from functools import partial
from io import BytesIO
from pathlib import Path
from typing import Dict, Union, List, Any, Tuple

import pandas as pd
from django.conf import settings
from lxml.etree import SubElement, register_namespace, QName, Element, tostring
from requests.compat import urljoin

from metadata.models import Report, ExtractionTransfer, ExternalRecord, ProcessingStep

__REPORT_TYPE_INDEX = {"arsberattelse": Report.DocumentType.ANNUAL_REPORT,
                       "verksamhetsberattelse": Report.DocumentType.ANNUAL_REPORT,
                       "revisionsberattelse": Report.DocumentType.FINANCIAL_STATEMENT}

__DUMMY_DIR = Path(__file__).parent.resolve() / "dummy_content"


def __parseDateString(dateString: str) -> datetime:
    if len(dateString) == 4:
        return datetime(int(dateString), 1, 1)
    else:
        s = dateString.split("-")
        year = s[0]
        month = int(s[1]) if s[1].isnumeric() else 1
        day = int(s[2]) if s[2].isnumeric() else 1
        return datetime(int(year), month, day)


def parseFilename(filename: str) -> Dict[str, Union[int, str, List[str], List[datetime]]]:
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

    s = filename.split("_")
    if len(s) < 3:
        raise SyntaxError(
            "The provided filename does not follow one of the expected patterns. Could not identify one or more of the "
            "following: union identifier, report type, report date(s)")

    unionId = s[0].lstrip("0") or "0"

    typeName = s[1]
    typeName = typeName.lower()
    typeName = typeName.replace("ä", "a")
    typeName = typeName.replace("å", "a")
    typeName = typeName.replace("ö", "o")
    if typeName in __REPORT_TYPE_INDEX:
        reportType = __REPORT_TYPE_INDEX[typeName]
    else:
        reportType = Report.DocumentType.ANNUAL_REPORT

    dates = set()
    page = 1
    for remainder in s[2:]:
        if "sid" in remainder:
            matches = re.findall(r"(?<=sid-)\d*", filename)
            page = int(matches[0])
        elif remainder.isalpha():
            continue
        else:
            if "och" in remainder:
                d = remainder.split("och")
                dates.add(__parseDateString(d[0].strip()))
                dates.add(__parseDateString(d[1].strip()))
            elif "--" in remainder:
                d = remainder.split("--")
                start = __parseDateString(d[0].strip())
                end = __parseDateString(d[1].strip())
                dates.add(start)
                y = start.year + 1
                while y < end.year:
                    dates.add(datetime(y, 1, 1))
                    y += 1
                dates.add(end)
            elif re.match("\d{4}-\d{4}", remainder):
                d = remainder.split("-")
                dates.add(__parseDateString(d[0]))
                dates.add(__parseDateString(d[1]))
            elif len(remainder) >= 4:
                dates.add(__parseDateString(remainder))
            else:
                continue

    if not dates:
        raise SyntaxError(
            "The provided filename does not follow one of the expected patterns. Could not identify one or more of the "
            "following: union identifier, report type, report year(s)")

    return {"date": sorted(list(dates)), "union_id": unionId, "type": reportType, "page": page}


def buildReportIdentifier(data: Dict[str, Union[str, int, List[datetime]]]) -> str:
    reportDates = data["date"]
    if isinstance(reportDates, list):
        dateRepr = "--".join([str(d) for d in sorted(reportDates)])
    else:
        dateRepr = str(reportDates)

    reportType = data["type"]
    if isinstance(reportType, list):
        reportType = "-".join(sorted(reportType))

    return f"{data['union_id']}-{reportType}-{dateRepr}"


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


def __isRestricted__(report: Report) -> bool:
    return report.accessRights == Report.AccessRights.RESTRICTED


def __buildOmekaSummaries__(transfer: ExtractionTransfer, checkRestriction: bool = False, forArab: bool = False) -> \
        Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    reportSummary = []
    pageSummary = []
    for report in transfer.report_set.all():
        # TODO: add null/none checks!!
        reportEntry = {"dcterms:identifier": report.identifier,
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
                       "dcterms:description": report.description}
        for translation in report.reporttranslation_set.all():
            language = translation.language
            reportEntry.update({f"dcterms:coverage.{language}": translation.coverage,
                                f"dcterms:type.{language}": __toOmekaList__(translation.type),
                                f"dcterms:isFormatOf.{language}": __toOmekaList__(translation.isFormatOf),
                                f"dcterms:accessRights.{language}": translation.accessRights,
                                f"dcterms:description.{language}": translation.description})

        reportSummary.append(reportEntry)

        if checkRestriction and __isRestricted__(report):
            transcription = ("FOLKRÖRELSEARKVET FÖR UPPSALA LÄN The contents of this report are "
                             "not publicly available. Please contact Folkrörelsearkivet för "
                             "Uppsala Län for more information. Email: info@fauppsala.se "
                             "https://www.fauppsala.se/kontakt/ FOLKRÖRELSEARKIVET FÖR UPPSALA "
                             "LÄN")
            if forArab:
                transcription = ("THE CONTENTS OF THIS REPORT ARE NOT PUBLICLY AVAILABLE. PLEASE CONTACT "
                                 "ARBETARRÖRELSENS ARKIV OCH BIBLIOTEK FOR MORE INFORMATION. INFO@ARBARK.SE "
                                 "WWW.ARBARK.SE/KONTAKT ARBETARRÖRELSENS ARKIV OCH BIBLIOTEK Swedish Labour Movement's "
                                 "Archvies and Library")

            pageSummary.append({"dcterms:isPartOf": report.identifier,
                                "dcterms:identifier": urljoin(settings.IIIF_BASE_URL,
                                                              f"iiif/image/{report.noid}_1/info.json"),
                                "lm:transcription": transcription, "lm:normalised": "", "lm:person": "",
                                "lm:organisation": "", "lm:location": "", "lm:time": "", "lm:work": "", "lm:event": "",
                                "lm:object": "", "lm:measure": False})
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


def buildTransferCsvs(transfer: ExtractionTransfer, checkRestriction: bool = False, forArab: bool = False):
    reportSummary, pageSummary = __buildOmekaSummaries__(transfer, checkRestriction, forArab=forArab)

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

        if checkRestriction and __isRestricted__(report):
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


def buildNormalizationCsv(srcNames, withPreservation: bool = True) -> str:
    data = []
    for f in srcNames:
        if f.endswith(".jpg"):
            if withPreservation:
                data.append((f, f"manualNormalization/access/{f}", f"manualNormalization/preservation/{f[:-4]}.tif"))
            else:
                data.append((f, f"manualNormalization/access/{f}", ""))
        else:
            data.append((f"transcription/{f}", "", ""))
    df = pd.DataFrame.from_records(data)
    return df.to_csv(header=False, index=False)


def buildMetadataCsv(transfer: ExtractionTransfer, checkRestriction: bool = False) -> str:
    records = []

    for report in transfer.report_set.all():
        translation = report.reporttranslation_set.filter(language="sv")
        if translation:
            translation = translation.first()
            dcType = __toCSList__(translation.type)
            dcCoverage = translation.coverage
            dcAccessRights = translation.accessRights
            dcFormat = f"{translation.description} - {__toCSList__([translation.isFormatOf])}"
        else:
            dcType = __toCSList__([Report.DocumentType[x].label for x in report.type])
            dcCoverage = Report.UnionLevel[report.coverage].label
            dcAccessRights = Report.AccessRights[report.accessRights].label
            dcFormat = f"{report.description} - {__toCSList__([Report.DocumentFormat[x].label for x in report.isFormatOf])}"

        if checkRestriction and __isRestricted__(report):
            row = {"dc.identifier": report.noid,
                   "dc.type": dcType,
                   "dc.date": "/".join([str(d.year) for d in report.date]),
                   "dc.language": __toCSList__(report.language),
                   "dc.coverage": dcCoverage,
                   "dc.title": report.title,
                   "dc.creator": report.creator,
                   "dc.source": __toCSList__(report.source),

                   "dc.relation": __toCSList__(report.relation),
                   "dc.format": dcFormat,
                   # "dc.description": report.description, # TODO: ???
                   "dc.rights1": dcAccessRights,
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
                   "dc.type": dcType,
                   "dc.date": "/".join([str(d.year) for d in report.date]),
                   "dc.language": __toCSList__(report.language),
                   "dc.coverage": dcCoverage,
                   "dc.title": report.title,
                   "dc.creator": report.creator,
                   "dc.source": __toCSList__(report.source),
                   "dc.relation": __toCSList__(report.relation),
                   "dc.format": dcFormat,
                   # "dc.description": report.description, # TODO: ???
                   "dc.rights1": dcAccessRights,
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


def buildFolderStructure(transfer: ExtractionTransfer, checkRestriction: bool = False, forArab: bool = False):
    dummyFileName = "page_not_available"
    if forArab:
        dummyFileName = "arab_restricted"

    outfile = BytesIO()
    filenames = []

    with zipfile.ZipFile(outfile, 'w', zipfile.ZIP_DEFLATED) as zf:
        zif = zipfile.ZipInfo("manualNormalization/access/")
        zf.writestr(zif, "")

        if not forArab:
            zif = zipfile.ZipInfo("manualNormalization/preservation/")
            zf.writestr(zif, "")

        for report in transfer.report_set.all():
            if checkRestriction and __isRestricted__(report):
                page_name = f"page_not_available_{report.noid}"
                zf.write(__DUMMY_DIR / f"{dummyFileName}.jpg", f"manualNormalization/access/{page_name}.jpg")
                zf.write(__DUMMY_DIR / f"{dummyFileName}.jpg", f"{page_name}.jpg")

                if not forArab:
                    zf.write(__DUMMY_DIR / f"{dummyFileName}.tif",
                             f"manualNormalization/preservation/{page_name}.tif")

                filenames.append(f"{page_name}.xml")
                filenames.append(f"{page_name}.jpg")

                zf.write(__DUMMY_DIR / f"{dummyFileName}.xml", f"transcription/{page_name}.xml")
            else:
                for page in report.page_set.all():
                    pageFileName = page.originalFileName
                    filenames.append(pageFileName)
                    filenames.append(str(Path(pageFileName).with_suffix(".jpg")))
                    zf.write(page.transcriptionFile.path, f"transcription/{pageFileName}")

        filenames.sort(key=lambda x: (x[-3:], x[:-4]))

        # zf.writestr("normalization.csv", buildNormalizationCsv(filenames, withPreservation=(not forArab)))

        zf.writestr("metadata/metadata.csv", buildMetadataCsv(transfer, checkRestriction))
        zf.writestr("metadata/mets_structmap.xml", buildStructMap(transfer, checkRestriction))

        reportSummary, pageSummary = __buildOmekaSummaries__(transfer, checkRestriction, forArab=forArab)
        zf.writestr("items.csv", pd.DataFrame.from_records(reportSummary).to_csv(index=False))
        zf.writestr("media.csv", pd.DataFrame.from_records(pageSummary).to_csv(index=False))

        zf.close()
    outfile.seek(0)

    return outfile


def updateExternalRecords(df: pd.DataFrame):
    df = df.fillna("")

    cols = df.columns
    if settings.ER_ARCHIVE_ID not in cols:
        raise ValueError(f"No column with name '{settings.ER_ARCHIVE_ID}' found in CSV.")
    if settings.ER_ORGANISATION_NAME not in cols:
        raise ValueError(f"No column with name '{settings.ER_ORGANISATION_NAME}' found in CSV.")

    for key in [settings.ER_COUNTY, settings.ER_MUNICIPALITY, settings.ER_CITY, settings.ER_PARISH,
                settings.ER_CATALOGUE_LINK, settings.ER_IS_VERSION_OF_LINK]:
        if key not in cols:
            df[key] = ""

    if settings.ER_COVERAGE not in cols:
        df[settings.ER_COVERAGE] = ""

    ExternalRecord.objects.bulk_create([ExternalRecord(archiveId=row[settings.ER_ARCHIVE_ID],
                                                       organisationName=row[settings.ER_ORGANISATION_NAME],
                                                       county=row[settings.ER_COUNTY],
                                                       municipality=row[settings.ER_MUNICIPALITY],
                                                       city=row[settings.ER_CITY], parish=row[settings.ER_PARISH],
                                                       relationLink=row[settings.ER_RELATION_LINK],
                                                       coverage=row[settings.ER_COVERAGE],
                                                       isVersionOfLink=row[settings.ER_IS_VERSION_OF_LINK]) for _, row
                                        in df.iterrows()
                                        if row[settings.ER_ARCHIVE_ID] and row[settings.ER_ORGANISATION_NAME]],
                                       update_conflicts=True, unique_fields=["archiveId"],
                                       update_fields=["organisationName", "county", "municipality", "city",
                                                      "relationLink", "coverage", "isVersionOfLink"],
                                       )


def buildProcessingSteps(config, job):
    if not config:
        raise TypeError("no config was supplied")
    if not job:
        raise TypeError("no job was supplied")

    for entry in config:
        ProcessingStep.objects.create(job=job, order=entry["stepType"].order,
                                      processingStepType=entry["stepType"].value,
                                      humanValidation=entry["humanValidation"], mode=entry["mode"])
