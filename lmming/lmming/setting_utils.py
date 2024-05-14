from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import tomli


@dataclass(init=False)
class GeneralSettings():
    archive: str = "FAC"

    def __init__(self, values: Dict[str, Any]):
        if "archive" in values:
            self.archive = values["archive"]


@dataclass(init=False)
class FilemakerSettings():
    archiveId: str = "PostID_Arkivbildare"
    organisationName: str = "Organisation"
    county: str = "Distrikt län"
    municipality: str = "Kommun"
    city: str = "Ort"
    parish: str = "Socken"

    def __init__(self, values: Dict[str, Any]):
        if "archiveId" in values:
            self.archiveId = values["archiveId"]
        if "organisationName" in values:
            self.organisationName = values["organisationName"]
        if "county" in values:
            self.county = values["county"]
        if "municipality" in values:
            self.municipality = values["municipality"]
        if "city" in values:
            self.city = values["city"]
        if "parish" in values:
            self.parish = values["parish"]


@dataclass(init=False)
class LoggingSettings():
    a: str = " "

    def __init__(self, values: Dict[str, Any]):
        pass


@dataclass
class Settings():
    general: GeneralSettings
    filemaker: FilemakerSettings
    logging: LoggingSettings


def loadSettingsFromToml(tomlPath: Path) -> Settings:
    with tomlPath.open("rb") as inFile:
        toml = tomli.load(inFile)
    filemakerSettings = FilemakerSettings(toml["filemaker"] if "filemaker" in toml else {})
    generalSettings = GeneralSettings(toml["general"] if "general" in toml else {})
    logginSettings = LoggingSettings(toml["loggin"] if "loggin" in toml else {})
    return Settings(general=generalSettings, filemaker=filemakerSettings, logging=logginSettings)
