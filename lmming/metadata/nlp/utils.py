import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List


def correction(entity):
    if len(entity) == 1:  # removes initials and single digits
        # (R): should this return an empty string? It would still evaluate to false on the outside but would allow this
        # method to consistently return a string (empty or not), instead of sometimes string, sometimes None?
        pass
    elif entity.startswith(".") and entity[1] == " ":  # ".Nemeth" > "Nemethh"
        return entity[2:]
    elif entity.startswith(".") and entity[1] != " ":  # ". Nemeth" > "Nemeth"
        return entity[1:]
    else:
        return entity


def handleLinebreakChars_original(line: str) -> str:
    text = ''
    if line[0] == "=":
        line = line[1:]
    if line[-1] == '¬' and line[-2] != "=" and line[-2] != '-':
        text += line[:-1] + ' '
    elif line[-1] == '¬' and line[-2] == "=":
        text += line[:-2]
    elif line[-1] == '¬' and line[-2] == "-":
        text += line[:-2]
    elif line[-1] == '-' and line[-2] != ':':
        text += line[:-1]
    else:
        text += line + ' '
    return text


def handleLinebreakChars(line: str) -> str:
    if not line:
        return line

    if line in ["=", "-", "¬"]:
        return ""
        # TODO: what should be returned in this case? symbol + 1 space?

    if line[0] == "=":
        line = line[1:]

    if line[-1] == "¬":
        line = line[:-1]
        if line[-1] in ["=", "-"]:
            return line[:-1]
        else:
            return line + " "
    elif line[-1] == "-":
        if line[-2] != ":":
            return line[:-1]
        else:
            return line + " "
    else:
        return line + " "


def __extractFromAlto__(root):
    namespace = {"": root.tag.split("}")[0].strip("{")}
    textLines = root.findall(".//TextLine", namespace)
    lines = []
    for tL in textLines:
        content = []
        for entry in tL:
            if entry.tag.endswith("SP"):
                content.append(" ")
            elif entry.tag.endswith("String"):
                content.append(entry.attrib["CONTENT"])
        lines.append("".join(content))
    return lines


def __extractFromPage__(root):
    namespace = {"": root.tag.replace("PcGts", "").strip("{}")}
    textLines = root.findall(".//TextLine/TextEquiv/Unicode", namespace)
    lines = []
    for line in textLines:
        text = line.text
        if not text:
            text = ""
        lines.append(text)

    return lines


def extractTranscriptionsFromXml(xmlFile: Path) -> List[str]:
    root = ET.parse(xmlFile).getroot()
    rootTag = root.tag
    if "alto" in rootTag:
        return __extractFromAlto__(root)
    elif "PcGts" in rootTag:
        return __extractFromPage__(root)
    else:
        # log issue
        return []
