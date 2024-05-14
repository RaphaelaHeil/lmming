import itertools
from pathlib import Path
from typing import Dict, List, Tuple, Set

from django.conf import settings


def loadAbbreviations() -> Dict[str, List[str]]:
    abbreviations = {}

    with (Path(settings.NER_BASE_DIR) / "abbreviations.txt").open("r") as inFile:
        lines = inFile.read().split("\n")
        for line in lines:
            entry = line.split(",")
            abbreviations[entry[0]] = entry[1:]
    return abbreviations


def loadSynonyms() -> Tuple[Dict[str, Set[str]], List]:
    dalin = {}
    with (Path(settings.NER_BASE_DIR) / "synonyms.txt").open("r") as inFile:
        pairs = inFile.read().split("\n")
        for pair in pairs:
            entry = pair.split(",")
            if entry[0] and entry[0] != entry[1]:
                if entry[0] not in dalin.keys():
                    dalin[entry[0]] = {entry[1]}
                else:
                    dalin[entry[0]].add(entry[1])

    dalin_values_flat = list(itertools.chain.from_iterable(dalin.values()))
    return dalin, dalin_values_flat


def get_key(val, dalin):
    for key, value in dalin.items():
        if val in value:
            return key
