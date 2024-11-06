from dataclasses import dataclass
from typing import Dict


@dataclass
class LanguageDictionary:
    coverage: Dict[str, str]
    type: Dict[str, str]
    isFormatOf: Dict[str, str]
    accessRights: Dict[str, str]


SWEDISH = LanguageDictionary(
    coverage={"workplace": "arbetsplats", "section": "sektion", "division": "avdelning", "district": "distrikt",
              "national branch": "nationellt förbund", "national federation": "nationell federation",
              "international branch": "internationell branschspecifik",
              "international federation": "internationell federation", "other": "övrig"},
    type={"annual report": "verksamhetsberättelse", "financial statement": "årsredovisning"},
    isFormatOf={"printed": "tryckt", "handwritten": "handskriven", "typewritten": "maskinskriven",
                "digital": "digital"},
    accessRights={"restricted": "tillståndsbelagt", "not restricted": "öppet"})
