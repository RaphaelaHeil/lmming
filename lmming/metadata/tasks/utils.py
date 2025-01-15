import dataclasses
import json
import os
from base64 import b64encode, b64decode
from datetime import date
from pathlib import Path
from typing import List, Dict

import requests
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from requests import Timeout, ConnectionError, TooManyRedirects

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


def getArabCoverage(coverage: str) -> Report.UnionLevel:
    coverage = coverage.lower()
    for value, label in Report.UnionLevel.choices:
        if value.lower() == coverage or label.lower() == coverage:
            return Report.UnionLevel[value]
    else:
        return Report.UnionLevel.OTHER


def splitIfNotNone(value: str) -> List[str]:
    if value:
        return [x.strip() for x in value.split(",")]
    else:
        return []


def createArabTitle(unionName: str, dates: List[date]) -> str:
    if not unionName:
        raise TypeError("no union name was supplied")

    if not dates:
        raise TypeError("no dates were supplied")

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

    return f"{unionName} {dateString}"


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


def generateClientNonceBytes():
    return bytearray(os.urandom(16))


def signBytesSHA256(bytesArray, pathToPrivateKeyPemFile):
    key = open(pathToPrivateKeyPemFile, "r").read()
    rsakey = RSA.importKey(key)
    signer = PKCS1_v1_5.new(rsakey)
    digest = SHA256.new()
    digest.update(bytesArray)
    sign = signer.sign(digest)
    return sign


def createAuthenticationString(user, userKeyFile, sessionId, serverNonceBytes):
    clientNonceBytes = generateClientNonceBytes()
    clientNonceString = b64encode(clientNonceBytes).decode("utf-8")
    combinedNonceBytes = serverNonceBytes + clientNonceBytes
    signatureBytes = signBytesSHA256(combinedNonceBytes, userKeyFile)
    signatureString = b64encode(signatureBytes).decode("utf-8")

    return (f'Handle sessionId="{sessionId}", cnonce="{clientNonceString}", id="{user}", type="HS_PUBKEY", '
            f'alg="SHA256", signature="{signatureString}"')


@dataclasses.dataclass
class HandleLocation:
    weight: int
    href: str
    view: str = ""

    def toXml(self):
        return f'<location href="{self.href}" weight="{self.weight}" {"view=\"" + self.view + "\"" if self.view else ""}/>'


class HandleError(Exception):

    def __init__(self, userMessage: str, adminMessage: str):
        super().__init__(userMessage, adminMessage)
        self.userMessage = userMessage
        self.adminMessage = adminMessage


class HandleAdapter(metaclass=Singleton):

    def __init__(self, address: str, port: int, prefix: str, user: str, userKeyFile: Path, certificateFile: Path,
                 userIndex: int = 300):
        self.prefix = prefix
        self.user = user
        self.userIndex = userIndex
        self.userKeyFile = userKeyFile
        self.certificateFile = False # disable checks until cert issues have been fixed ...
        self.sessionId = ""
        self.serverNonce = ""
        self.serverNonceBytes = b""

        if address.startswith("https://"):
            self.baseUrl = f"{address}:{port}"
        else:
            self.baseUrl = f"https://{address}:{port}"

    def __isHandleSessionActive(self):
        if not self.sessionId or not self.serverNonce:
            return False

        try:
            response = requests.get(url=f"{self.baseUrl}/api/sessions/this", verify=self.certificateFile,
                                    headers={"Authorization": f'Handle sessionId="{self.sessionId}"'})

            if response.ok:
                responseJson = response.json()
                if "sessionId" in responseJson and "nonce" in responseJson:
                    if responseJson["sessionId"] == self.sessionId and responseJson["nonce"] == self.serverNonce:
                        return True
                return False
            else:
                return False
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError(
                "Connectivity issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def __updateSession(self):
        url = f"{self.baseUrl}/api/sessions"

        try:
            initialResponse = requests.post(url=url, headers={"Authorization": "Handle version=0"},
                                            verify=self.certificateFile)

            content = initialResponse.json()
            sessionId = content["sessionId"]
            serverNonce = content["nonce"]
            serverNonceBytes = b64decode(serverNonce)

            authorizationHeaderString = createAuthenticationString(self.user, self.userKeyFile, sessionId,
                                                                   serverNonceBytes)

            headers = {
                "Content-Type": "application/json",
                "Authorization": authorizationHeaderString
            }

            response = requests.post(url=url + "/this", headers=headers, verify=self.certificateFile)
            if response.ok:
                self.sessionId = sessionId
                self.serverNonce = serverNonce
                self.serverNonceBytes = serverNonceBytes
            else:
                raise HandleError("Could not authenticate at handle server. Please try again later, and contact your "
                                  "admin if the issue persists.",
                                  f"Session could not be established: {response.status_code} - {response.content}")
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError(
                "Connectivity issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def doesHandleAlreadyExist(self, noid) -> bool:
        try:
            response = requests.get(url=f"{self.baseUrl}/api/handles/{self.prefix}/{noid}", verify=self.certificateFile)
            if response.ok:
                return True
            else:
                return False
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError(
                "Connectivity issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def updateLocationBasedHandle(self, noid: str, locations: List[HandleLocation]):
        try:
            if not self.__isHandleSessionActive():
                self.__updateSession()

            authorizationHeaderString = createAuthenticationString(self.user, self.userKeyFile, self.sessionId,
                                                                   self.serverNonceBytes)
            headers = {"Content-Type": "application/json", "Authorization": authorizationHeaderString}

            locationString = "<locations>" + "".join(x.toXml() for x in locations) + "</locations>"

            handleRecord = {"values": [{"index": 100, "type": "HS_ADMIN",
                                        "data": {"format": "admin", "value": {"handle": self.user, "index": 200,
                                                                              "permissions": "011111110011"}}},
                                       {"index": 1000, "type": "10320/loc",
                                        "data": {"format": "string", "value": locationString}}
                                       ]}
            response = requests.put(url=f"{self.baseUrl}/api/handles/{self.prefix}/{noid}", headers=headers,
                                    verify=self.certificateFile, data=json.dumps(handleRecord))
            if response.ok:
                return f"{self.prefix}/{noid}"
            else:
                raise HandleError(f"Could not update handle {self.prefix}/{noid} - please try again, and contact your "
                                  f"admin if the issue persists.",
                                  f"Could not update handle {self.prefix}/{noid} - response: {response.status_code} - "
                                  f"{response.content}")

        except HandleError as exception:
            raise exception
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError("Connectivity issues occurred. Please try again later, and contact your admin if the "
                              "issue persists.", f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def createLocationBasedHandle(self, noid: str, locations: List[HandleLocation]):
        try:
            if self.doesHandleAlreadyExist(noid):
                raise HandleError(f"Handle '{self.prefix}/{noid}' already exists",
                                  f"Handle '{self.prefix}/{noid}' already exists")
            return self.updatePlainHandle(noid, locations)
        except HandleError as e:
            if "update" in e.userMessage:
                e.userMessage.replace("update", "create")
                e.adminMessage.replace("update", "create")
            raise e

    def updatePlainHandle(self, noid, resolveTo) -> str:
        try:
            if not self.__isHandleSessionActive():
                self.__updateSession()

            authorizationHeaderString = createAuthenticationString(self.user, self.userKeyFile, self.sessionId,
                                                                   self.serverNonceBytes)
            headers = {"Content-Type": "application/json", "Authorization": authorizationHeaderString}

            handleRecord = {"values": [{"index": 1, "type": "URL", "data": {"format": "string", "value": resolveTo}},
                                       {"index": 100, "type": "HS_ADMIN", "data": {"format": "admin",
                                                                                   "value": {"handle": self.user,
                                                                                             "index": 200,
                                                                                             "permissions": "011111110011"}}}]}
            response = requests.put(url=f"{self.baseUrl}/api/handles/{self.prefix}/{noid}", headers=headers,
                                    verify=self.certificateFile, data=json.dumps(handleRecord))
            if response.ok:
                return f"{self.prefix}/{noid}"
            else:
                raise HandleError(f"Could not update handle {self.prefix}/{noid} - please try again, and contact your "
                                  f"admin if the issue persists.",
                                  f"Could not update handle {self.prefix}/{noid} - response: {response.status_code} - "
                                  f"{response.content}")

        except HandleError as exception:
            raise exception
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError("Connectivity issues occurred. Please try again later, and contact your admin if the "
                              "issue persists.", f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def createPlainHandle(self, noid:str, resolveTo:str) -> str:
        try:
            if self.doesHandleAlreadyExist(noid):
                raise HandleError(f"Handle '{self.prefix}/{noid}' already exists",
                                  f"Handle '{self.prefix}/{noid}' already exists")
            return self.updatePlainHandle(noid, resolveTo)
        except HandleError as e:
            if "update" in e.userMessage:
                e.userMessage.replace("update", "create")
                e.adminMessage.replace("update", "create")
            raise e


class ArkError(Exception):

    def __init__(self, userMessage: str, adminMessage: str):
        super().__init__(userMessage, adminMessage)
        self.userMessage = userMessage
        self.adminMessage = adminMessage


class ArkletAdapter:

    def __init__(self, address: str, naan: str, authenticationToken: str):
        self.arkletBaseUrl = address
        self.naan = naan
        self.headers = {"Authorization": f"Bearer {authenticationToken}"}

        if self.arkletBaseUrl.endswith("/"):
            self.arkletBaseUrl = self.arkletBaseUrl.rstrip("/")

    def createArk(self, shoulder: str, details: Dict[str, str]) -> str:
        mintUrl = self.arkletBaseUrl + "/mint"
        mintBody = {"naan": self.naan, "shoulder": shoulder}
        mintBody.update(details)
        response = requests.post(mintUrl, headers=self.headers, json=mintBody)
        if response.ok:
            ark = response.json()["ark"]
            if ark:
                return ark
            else:
                raise ArkError(f"Arklet did not return a new ARK. Please contact your admin.",
                               f"Arklet returned empty ARK for shoulder {shoulder}")
        else:
            raise ArkError(
                f"An error occurred while obtaining a new ARK, reason: {response.status_code} {response.reason}. "
                f"Please verify that Arklet is running and try again.",
                f"Error creating ARK, reason: {response.status_code} {response.reason}")

    def updateArk(self, noid: str, details: Dict[str, str]):
        ark = f"ark:/{self.naan}/{noid}"
        details["ark"] = ark

        response = requests.put(url=self.arkletBaseUrl + "/update", headers=self.headers, json=details)
        if not response.ok:
            raise ArkError(
                f"An error occurred while updating the ARK {ark} ({response.status_code} {response.reason}).",
                f"Error updating ARK {ark}, reason: {response.status_code} {response.reason}")

    def createArkWithDependentUrl(self, shoulder: str, urlFormat: str, details: Dict[str, str]) -> str:
        ark = self.createArk(shoulder, details)
        noid = ark.split("/")[-1]

        url = urlFormat.format(noid)
        details["url"] = url
        self.updateArk(noid, details)
        return ark
