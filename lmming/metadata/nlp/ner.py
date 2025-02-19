import re
from dataclasses import dataclass, field
from pathlib import Path
from string import capwords
from typing import List

import nltk

nltk.download('punkt_tab')
from .aux import loadAbbreviations, loadSynonyms, get_key
from .hf_utils import getKBPipeline, getHistbertPipeline
from .utils import correction, handleLinebreakChars, extractTranscriptionsFromXml

TIME_EXPRESSIONS = ["Januari", "januari", "Jan", "jan", "Februari", "februari", "Feb", "feb", "Mars", "mars", "Mar",
                    "mar", "April", "april", "Apr", "apr", "Maj", "maj", "Juni", "juni", "Jun", "jun", "Juli", "juli",
                    "Jul", "jul", "Augusti", "augusti", "Aug", "aug", "September", "september", "Sept", "sept",
                    "Oktober", "oktober", "Okt", "okt", "November", "november", "Nov", "nov", "December", "december",
                    "Dec", "dec"]
VOWELS = "[aeiouäöåAEIOUÄÖÅ]"
CONSONANTS = "[bcdfghjklmnpqrstvwxyz]"

EMPTY = ""


@dataclass
class NlpResult:
    text: str = ""
    normalised: str = ""
    persons: List[str] = field(default_factory=list)
    organisations: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)
    times: List[str] = field(default_factory=list)
    works: List[str] = field(default_factory=list)
    events: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    measures: bool = False

    def removeDuplicates(self):
        self.persons = list(dict.fromkeys(self.persons))
        self.organisations = list(dict.fromkeys(self.organisations))
        self.locations = list(dict.fromkeys(self.locations))
        self.times = list(dict.fromkeys(self.times))
        self.works = list(dict.fromkeys(self.works))
        self.events = list(dict.fromkeys(self.events))
        self.objects = list(dict.fromkeys(self.objects))


class NerHelper:

    def __init__(self):
        self.ABBREVIATIONS = loadAbbreviations()
        self.DALIN, self.DALIN_VALUES_FLAT = loadSynonyms()

        self._ner_ra = None
        self._ner_kb = None

    @property
    def NER_RA(self):
        if not self._ner_ra:
            self._ner_ra = getHistbertPipeline()
        return self._ner_ra

    @property
    def NER_KB(self):
        if not self._ner_kb:
            self._ner_kb = getKBPipeline()
        return self._ner_kb


NER_HELPER = NerHelper()


def normalize(document):
    edited = ''
    processed = nltk.word_tokenize(document)
    for word in processed:
        if word in NER_HELPER.ABBREVIATIONS.keys():
            word = NER_HELPER.ABBREVIATIONS[word][0]
        if word in NER_HELPER.DALIN_VALUES_FLAT:
            normalized = get_key(word, NER_HELPER.DALIN)
            edited += normalized + ' '
        else:
            # Rule #1 qvart > kvart
            normalized = re.sub(r"(Qv)", r"Kv", word)
            normalized = re.sub(r"(qv)", r"kv", normalized)
            # Rule #2 hvilket > vilket, wid > vid
            normalized = re.sub(r"^(hv|w)", r"v", normalized)
            normalized = re.sub(r"^(Hv|W)", r"V", normalized)
            # Rule #3 lefuer > lever, hafva > hava
            normalized = re.sub(r"(%s)ff?[uv](%s)" % (VOWELS, VOWELS), r"\1v\2", normalized)
            # Rule #4 fördärfvat > fördärvat, blijfva > bliva
            normalized = re.sub(r"j?fv", r"v", normalized)
            # Rule #5 een > en, saak > sak
            normalized = re.sub(r"(%s)\1{1}" % VOWELS, r"\1", normalized)
            # Rule #6 ähr > är, ahntaga > antaga
            normalized = re.sub(r"(%s)h([nr])" % VOWELS, r"\1\2", normalized)
            # Rule #7 uthfhöra > utföra, sägher > säger
            # normalized = re.sub(r"([dtfgk])h", r"\1", normalized)
            # Rule #8 elliest > eljest, bevilliat > beviljat
            normalized = re.sub(r"lli([ae])", r"lj\1", normalized)
            # Rule #9 varidt > varit
            normalized = re.sub(r"födt", r"fött", normalized)
            normalized = re.sub(r"dt", r"t", normalized)
            # Rule #10 dömbt > dömt, benämbdh > benämnd
            normalized = re.sub(r"m[bp]t", r"mt", normalized)
            normalized = re.sub(r"m[bp]d", r"mnd", normalized)
            # Rule #11 slogz > slogs, skötz > sköts
            normalized = re.sub(r"z", r"s", normalized)
            # Rule #12 försöria > försörja
            # normalized = re.sub(r"([^a])ria([^t]|$)", r"\1rja\2", normalized)
            # Rule #13 vijka > vika, bevijsa > bevisa
            normalized = re.sub(r"iji", r"j", normalized)
            normalized = re.sub(r"ij", r"i", normalized)
            # Rule #14 häfdar > hävdar
            normalized = re.sub(r"(%s)fd" % VOWELS, r"\1vd", normalized)
            # Rule #15 föregaf > föregav
            normalized = re.sub(r"gaff?($|\s)", r"gav\1", normalized)
            # Rule #16 blef > blev
            normalized = re.sub(r"eff?($|\s)", r"ev\1", normalized)
            # Rule #17 affsagt > avsagt
            normalized = re.sub(r"^([Aa])ff", r"\1v", normalized)
            # Rule #18 schall > skall
            normalized = re.sub(r"sch", r"sk", normalized)
            # Rule #19 kiöpt > köpt
            normalized = re.sub(r"kiö", r"kö", normalized)
            # Rule #20 prætenderat > pretenderat
            normalized = re.sub(r"(æ|ae)", r"e", normalized)
            # Rule #21 ehrläggia > erlägga, sökia > söka
            normalized = re.sub(r"(gg|k)ia", r"\1a", normalized)
            # Rule #22 huilken > vilken
            normalized = re.sub(r"hui", r"vi", normalized)
            # Rule #23 avsachnat > avsaknat
            normalized = re.sub(r"ch(%s)" % CONSONANTS, r"k\1", normalized)
            # Rule #24 giort > gjort
            normalized = re.sub(r"giort", r"gjort", normalized)
            # Rule #25 voro > vore
            normalized = re.sub(r"voro", r"vore", normalized)
            # Rule #26 effter > efter, offta > ofta
            normalized = re.sub(r"fft", r"ft", normalized)
            # Rule #27 givess > gives, avdömass > avdömas
            normalized = re.sub(r"([^o])ss($|\s)", r"\1s\2", normalized)
            # Rule #28 af > av
            normalized = re.sub(r"([Aa])f([^ft]|$)", r"\1v\2", normalized)
            # Rule #29 iemte > jämte, sielf > själv
            normalized = re.sub(r"ie(l|r|mt)", r"jä\1", normalized)
            normalized = re.sub(r"Ie(l|r|mt)", r"Jä\1", normalized)
            normalized = re.sub(r"(T|t)ien", r"\1jän", normalized)
            edited += normalized + ' '
    return edited


def __cutAddress(person: str) -> str:
    if person.lower().startswith("herr "):
        return person[5:]
    if person.lower().startswith("fröken "):
        return person[7:]
    return person


def __allCapsToPascal(person: str) -> str:
    return capwords(person)


def filtered_entities(text: str, result: NlpResult):
    msr = 0
    processed_ra = NER_HELPER.NER_RA(text)
    processed_kb = NER_HELPER.NER_KB(text)
    for element in processed_ra:
        entity = correction(element["word"])
        label = element["entity_group"]
        if entity:
            if label == "ORG":
                result.organisations.append(entity)
            elif label == "PRS":
                if not entity:
                    continue
                entity = __cutAddress(entity)
                if entity.isupper():
                    entity = __allCapsToPascal(entity)
                result.persons.append(entity)
    for element in processed_kb:
        entity = correction(element["word"])
        label = element["entity_group"]
        if entity and label == "TME" and not any(map(str.isdigit, entity)):  # This isn't working properly, check!
            for month in TIME_EXPRESSIONS:
                if month not in entity.split(' '):
                    pass
                else:
                    result.times.append(entity)
        elif entity and label == "MSR":
            msr += 1
        elif entity and label != "PER":
            # ent_final = {label: [] for label in ["ORG", "PRS", "TME", "OBJ", "LOC", "WRK", "EVN"]}
            match label:
                case "PRS":
                    if not entity:
                        continue
                    entity = __cutAddress(entity)
                    if entity.isupper():
                        entity = __allCapsToPascal(entity)
                    result.persons.append(entity)
                case "TME":
                    result.times.append(entity)
                case "ORG":
                    result.organisations.append(entity)
                case "OBJ":
                    result.objects.append(entity)
                case "LOC":
                    result.locations.append(entity)
                case "WRK":
                    result.works.append(entity)
                case "EVN":
                    result.events.append(entity)


def processPage(pagePath: Path, normalise: bool = True) -> NlpResult:
    result = NlpResult()
    if pagePath.suffix == ".xml":
        lines = extractTranscriptionsFromXml(pagePath)
    elif pagePath.suffix == ".txt":
        with pagePath.open("r") as inFile:
            lines = list(filter(None, inFile.read().splitlines()))
    else:
        # TODO: log
        lines = []
    text = ""
    for line in lines:
        text += handleLinebreakChars(line)
    result.text = text
    if normalise:
        result.normalised = normalize(text)
    else:
        result.normalised = text
    filtered_entities(result.normalised, result)
    result.removeDuplicates()
    return result
