from typing import List, Any


def __toDisplayList__(inputList: List[Any]) -> str:
    if inputList:
        return ", ".join([str(i) for i in inputList])
    else:
        return ""


def __fromDisplayList__(inputList: str) -> List[Any]:
    if inputList:
        return [s.strip() for s in inputList.split(",")]
    else:
        return []

