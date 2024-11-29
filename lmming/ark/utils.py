from typing import Dict

import requests
from django.conf import settings


def getArkDetails(url: str) -> Dict[str, str]:
    response = requests.get(url + "?json")
    if response.ok:
        return response.json()
    else:
        raise ValueError(f"Could not retrieve ARK details. Server resopnse: {response.status_code} - {response.reason}")


def updateArk(arkUrl: str, details: Dict[str, str]) -> Dict[str, str]:
    headers = {"Authorization": f"Bearer {settings.MINTER_AUTH}"}
    noid = arkUrl.split("ark:/")[1].split("/")[1]
    ark = f"ark:/{settings.MINTER_ORG_ID}/{noid}"
    details["ark"] = ark

    response = requests.put(url=settings.MINTER_URL + "/update", headers=headers, json=details)
    if response.ok:
        return response.json()
    else:
        raise ValueError(f"Could not update ARK details. Server response: {response.status_code} - {response.reason}")


def createArk(details: Dict[str, str]) -> Dict[str, str]:
    shoulder = "/r1"
    mintUrl = settings.MINTER_URL + "/mint"
    headers = {"Authorization": f"Bearer {settings.MINTER_AUTH}"}
    mintBody = {"naan": settings.MINTER_ORG_ID, "shoulder": shoulder}
    mintBody.update(details)
    response = requests.post(mintUrl, headers=headers, json=mintBody)
    if response.ok:
        ark = response.json()["ark"]
        if settings.MINTER_URL.count(":") > 1:
            url = ":".join(settings.MINTER_URL.split(":")[:2])
        mintBody["ark"] = url + "/" + ark
        return mintBody
    else:
        raise ValueError(f"Could not register new ARK. Server response: {response.status_code} - {response.reason}")
