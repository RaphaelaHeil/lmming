import json
import os
from base64 import b64encode, b64decode
from datetime import date
from pathlib import Path
from typing import List

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

    return (f'Handle sessionId="{sessionId}", cnonce="{clientNonceString}" id="{user}", type="HS_PUBKEY", '
            f'alg="SHA256", signature="{signatureString}"')


class HandleError(Exception):

    def __init__(self, userMessage: str, adminMessage: str):
        super().__init__(userMessage, adminMessage)
        self.userMessage = userMessage
        self.adminMessage = adminMessage


class HandleAdapter(metaclass=Singleton):

    def __init__(self, ip: str, port: int, prefix: str, user: str, userIndex: int, userKeyFile: Path):
        self.prefix = prefix
        self.user = user
        self.userIndex = userIndex
        self.userKeyFile = userKeyFile
        self.sessionId = ""
        self.serverNonce = ""
        self.serverNonceBytes = b""

        if ip.startswith("https://"):
            self.baseUrl = f"{ip}:{port}"
        else:
            self.baseUrl = f"https://{ip}:{port}"

    def __isHandleSessionActive(self):
        if not self.sessionId or not self.serverNonce:
            return False

        try:
            response = requests.get(url=f"{self.baseUrl}/api/sessions/this", verify=False,
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
                "Connectivitiy issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occcurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def __updateSession(self):
        url = f"{self.baseUrl}/api/sessions"

        try:
            initialResponse = requests.post(url, headers={"Authorization": "Handle version=0"}, verify=False)

            content = json.loads(initialResponse.content)
            sessionId = content["sessionId"]
            serverNonce = content["nonce"]
            serverNonceBytes = b64decode(serverNonce)

            authorizationHeaderString = createAuthenticationString(self.user, self.userKeyFile, sessionId,
                                                                   serverNonceBytes)

            headers = {
                "Content-Type": "application/json",
                "Authorization": authorizationHeaderString
            }

            response = requests.post(url + "/this", headers=headers, verify=False)
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
                "Connectivitiy issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occcurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def doesHandleAlreadyExist(self, noid) -> bool:
        try:
            response = requests.get(url=f"{self.baseUrl}/api/handles/{self.prefix}/{noid}", verify=False, )
            if response.ok:
                return True
            else:
                return False
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError(
                "Connectivitiy issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occcurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")

    def createHandle(self, noid, resolveTo) -> str:
        try:
            if not self.__isHandleSessionActive():
                self.__updateSession()
            if self.doesHandleAlreadyExist(noid):
                raise HandleError(f"Handle '{self.prefix}/{noid}' already exists",
                                  f"Handle '{self.prefix}/{noid}' already exists")

            authorizationHeaderString = createAuthenticationString(self.user, self.userKeyFile, self.sessionId,
                                                                   self.serverNonceBytes)
            headers = {"Content-Type": "application/json", "Authorization": authorizationHeaderString}

            handleRecord = {"values": [{"index": 1, "type": "URL", "data": {"format": "string", "value": resolveTo}},
                                       {"index": 100, "type": "HS_ADMIN", "data": {"format": "admin",
                                                                                   "value": {"handle": self.user,
                                                                                             "index": 200,
                                                                                             "permissions": "011111110011"}}}]}
            response = requests.put(url=f"{self.baseUrl}/api/handles/{self.prefix}/{noid}", headers=headers,
                                    verify=False,
                                    data=json.dumps(handleRecord))
            if response.ok:
                return f"{self.prefix}/{noid}"
            else:
                raise HandleError(
                    f"Could not create handle {self.prefix}/{noid} - please try again, and contact your admin if the issue persists.",
                    f"Could not create handle {self.prefix}/{noid} - response: {response.status_code} - {response.content}")

        except HandleError as exception:
            raise exception
        except (ConnectionError, Timeout, TooManyRedirects) as exception:
            raise HandleError(
                "Connectivitiy issues occurred. Please try again later, and contact your admin if the issue persists.",
                f"{type(exception).__name__} - {exception}")
        except Exception as exception:
            raise HandleError("An issue occcurred, Please try again later.",
                              f"{type(exception).__name__} - {exception}")
