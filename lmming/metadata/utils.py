import re
from typing import Dict, Union, List

from metadata.models import Report

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

    unionId = s[0]

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
