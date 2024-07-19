from typing import List

from metadata.models import Report


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
