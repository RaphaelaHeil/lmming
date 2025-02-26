import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, List

from v2.models import FileType

__FILETYPE_INDEX = {".jpg": FileType.IMAGE, ".jpeg": FileType.IMAGE, ".xml": FileType.XML, ".txt": FileType.PLAINTEXT,
                    ".pdf": FileType.PDF}


def __parseDateString(dateString: str) -> datetime:
    if len(dateString) == 4:
        return datetime(int(dateString), 1, 1)
    else:
        s = dateString.split("-")
        year = s[0]
        month = int(s[1]) if s[1].isnumeric() else 1
        day = int(s[2]) if s[2].isnumeric() else 1
        return datetime(int(year), month, day)


def parseFilename(file: str) -> Dict[str, Union[int, str, List[str], List[datetime]]]:
    extension = Path(file).suffix

    if extension in __FILETYPE_INDEX:
        fileType = __FILETYPE_INDEX[extension]
    else:
        fileType = FileType.OTHER

    filename = Path(file).stem

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
            elif re.match(r"\d{4}-\d{4}", remainder):
                d = remainder.split("-")
                dates.add(__parseDateString(d[0]))
                dates.add(__parseDateString(d[1]))
            elif len(remainder) >= 4 and remainder.replace("-", "").replace("_", "").replace(":", "").isnumeric():
                # prevent FAC fragments from ending up in this case ...
                dates.add(__parseDateString(remainder))
            else:
                continue

    if not dates:
        raise SyntaxError(
            "The provided filename does not follow one of the expected patterns. Could not identify one or more of the "
            "following: union identifier, report type, report year(s)")

    return {"date": tuple(sorted(list(dates))), "union_id": unionId, "type": typeName, "page": page,
            "fileType": fileType}


def extractFileData(files):
    result = []

    unionIds = set()
    typeNames = set()
    pages = set()
    dates = set()

    for file in files:
        data = parseFilename(file.name)
        data["file"] = file
        result.append(data)
        unionIds.add(data["union_id"])
        typeNames.add(data["type"])
        pages.add(data["page"])
        dates.add(data["date"])

    return result, unionIds, typeNames, pages, dates
