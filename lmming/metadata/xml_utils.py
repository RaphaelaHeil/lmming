from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List

from lxml import etree


@dataclass
class TextLine:
    id: str
    xCoords: List[int]
    yCoords: List[int]
    x0: int = 0
    x1: int = 0
    y0: int = 0
    y1: int = 0
    transcription: str = ""
    baseline: str = ""

    def __post_init__(self):
        self.x0 = min(self.xCoords)
        self.x1 = max(self.xCoords)
        self.y0 = min(self.yCoords)
        self.y1 = max(self.yCoords)


@dataclass
class TextRegion:
    id: str
    x0: int
    x1: int
    y0: int
    y1: int
    lines: List[TextLine] = field(default_factory=list)
    coordString: str = ""


@dataclass
class Page:
    regions: List[TextRegion] = field(default_factory=list)
    height: int = -1
    width: int = -1


def __parsePage(root) -> Page:
    parsedPage = Page()
    rootTag = root.tag
    if "PcGts" in rootTag:
        namespace = {"": rootTag.replace("PcGts", "").strip("{}")}
    else:
        namespace = {"": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"}
    pageElement = root.find("Page", namespace)
    parsedPage.height = pageElement.attrib["imageHeight"]
    parsedPage.width = pageElement.attrib["imageWidth"]

    for textRegion in pageElement.findall("TextRegion", namespace):
        trCoords = textRegion.find("Coords", namespace)
        if trCoords is None:
            continue
        coordString = trCoords.attrib["points"]
        coords = coordString.split()
        xCoords = [int(p.split(",")[0]) for p in coords]
        yCoords = [int(p.split(",")[1]) for p in coords]

        tR = TextRegion(id=textRegion.attrib["id"], x0=min(xCoords), x1=max(xCoords), y0=min(yCoords), y1=max(yCoords),
                        coordString=coordString)

        for line in textRegion.findall("TextLine", namespace):
            coords = line.find("Coords", namespace).attrib["points"].split()
            xCoords = [int(p.split(",")[0]) for p in coords]
            yCoords = [int(p.split(",")[1]) for p in coords]

            baseline = line.find("Baseline", namespace)
            baselineString = ""
            if baseline is not None:
                baselineString = baseline.attrib["points"]

            l = TextLine(id=line.attrib["id"], xCoords=xCoords, yCoords=yCoords, baseline=baselineString)

            textEquiv = line.find("TextEquiv", namespace)
            if textEquiv:
                unicodeText = textEquiv.find("Unicode", namespace).text
                if unicodeText:
                    l.transcription = unicodeText

            tR.lines.append(l)
        parsedPage.regions.append(tR)

    return parsedPage


def convertPageToAlto(filename: Path, pageRoot) -> str:
    page = __parsePage(pageRoot)

    templateString = ""
    with (Path( __file__ ).parent.absolute()/"alto_template.xml").open("r") as inFile:
        templateString = inFile.read()

    templateString = templateString.replace("{FILENAME}", filename.with_suffix(".jpg").name)
    templateString = templateString.replace("{PROCESSING_DATETIME}", datetime.now().isoformat())
    templateString = templateString.replace("{PAGE_HEIGHT}", str(page.height))
    templateString = templateString.replace("{PAGE_WIDTH}", str(page.width))

    parser = etree.XMLParser(remove_blank_text=True)

    root = etree.fromstring(templateString, parser=parser)

    rootTag = root.tag
    if "alto" in rootTag:
        namespace = {"alto": rootTag.split("}")[0].strip("{")}
    else:
        namespace = {"alto": "http://www.loc.gov/standards/alto/ns-v4#"}

    etree.register_namespace("alto", namespace["alto"])

    printSpace = root.xpath(".//alto:PrintSpace", namespaces=namespace)[0]

    for region in page.regions:
        regionElement = etree.SubElement(printSpace, etree.QName(namespace["alto"], "TextBlock"))
        regionElement.set("ID", str(region.id))
        regionElement.set("HEIGHT", str(region.y1 - region.y0))
        regionElement.set("WIDTH", str(region.x1 - region.x0))
        regionElement.set("VPOS", str(region.y0))
        regionElement.set("HPOS", str(region.x0))

        if region.coordString:
            shapeElement = etree.SubElement(regionElement, etree.QName(namespace["alto"], "Shape"))
            polygonElement = etree.SubElement(shapeElement, etree.QName(namespace["alto"], "Polygon"))
            polygonElement.set("POINTS", region.coordString)

        for line in region.lines:
            lineElement = etree.SubElement(regionElement, etree.QName(namespace["alto"], "TextLine"))
            lineElement.set("ID", str(line.id))
            if line.baseline:
                lineElement.set("BASELINE", line.baseline)
            lineElement.set("HEIGHT", str(line.y1 - line.y0))
            lineElement.set("WIDTH", str(line.x1 - line.x0))
            lineElement.set("VPOS", str(line.y0))
            lineElement.set("HPOS", str(line.x0))

            stringElement = etree.SubElement(lineElement, etree.QName(namespace["alto"], "String"))
            stringElement.set("ID", "string_" + line.id)
            stringElement.set("HEIGHT", str(line.y1 - line.y0))
            stringElement.set("WIDTH", str(line.x1 - line.x0))
            stringElement.set("VPOS", str(line.y0))
            stringElement.set("HPOS", str(line.x0))
            stringElement.set("CONTENT", line.transcription)

    return etree.tostring(root, pretty_print=True, encoding="utf-8").decode("utf-8")