from datetime import date
from typing import List

from metadata.models import Report


def resumePipeline(jobPk):
    from metadata.tasks.manage import scheduleTask
    scheduleTask(jobPk)


def getFacCoverage(unionName: str) -> Report.UnionLevel:
    unionName = unionName.lower()
    if "klubb" in unionName:
        return Report.UnionLevel.WORKPLACE
    elif "sektion" in unionName:
        return Report.UnionLevel.SECTION
    elif "avd" in unionName or "avdelning" in unionName:
        return Report.UnionLevel.DIVISION
    elif "distrikt" in unionName:
        return Report.UnionLevel.DISTRICT
    else:
        return Report.UnionLevel.OTHER


def getArabCoverage(unionName: str) -> Report.UnionLevel:
    unionName = unionName.lower()
    if "riks" in unionName:
        return Report.UnionLevel.NATIONAL_BRANCH
    elif "regional" in unionName:
        return Report.UnionLevel.DISTRICT
    elif "lokal" in unionName:
        return Report.UnionLevel.SECTION
    else:
        return Report.UnionLevel.OTHER


def splitIfNotNone(value: str) -> List[str]:
    if value:
        return [x.strip() for x in value.split(",")]
    else:
        return []


REPORT_SPELLINGS = {Report.DocumentType.ANNUAL_REPORT: "Annual Report",
                    Report.DocumentType.FINANCIAL_STATEMENT: "Financial Statement"}


def createArabTitle(reportTypes: List[Report.DocumentType], dates: List[date]) -> str:
    if not reportTypes:
        raise TypeError("no report types were supplied")
    if not dates:
        raise TypeError("no dates were supplied")

    for r in reportTypes:
        if r not in REPORT_SPELLINGS:
            raise ValueError(f"unknown report type {str(r)}")

    sortedReportTypes = sorted(set(reportTypes), key=lambda x: Report.DocumentType[x].label[0])

    typeString = ", ".join(REPORT_SPELLINGS[r] for r in sortedReportTypes)

    groupedDates = []
    sortedDates = sorted(set(dates))
    groupedDates.append([sortedDates.pop(0).year])
    for d in sortedDates:
        if d.year - 1 == groupedDates[-1][-1]:
            groupedDates[-1].append(d.year)
        else:
            groupedDates.append([d.year])

    dateString = ""
    for g in groupedDates:
        if dateString:
            dateString += ", "
        if len(g) > 1:
            dateString += f"{g[0]} -- {g[-1]}"
        else:
            dateString += f"{str(g[0])}"

    return f"{typeString} {dateString}"
