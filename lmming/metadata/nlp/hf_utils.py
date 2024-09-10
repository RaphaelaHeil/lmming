from enum import Enum
from pathlib import Path

import torch
from django.conf import settings
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline


def download():
    for modelName, revision in [("crina-t/histbert-finetuned-ner", settings.HF_CRINA_HASH),
                                ("KBLab/bert-base-swedish-cased-ner", settings.HF_KB_HASH)]:
        modelDir = Path(settings.NER_BASE_DIR) / "checkpoints" / modelName.replace("/", "_")
        versionFile = modelDir / "version.txt"
        if versionFile.exists():
            with versionFile.open("r") as inFile:
                existingRevision = inFile.read()
                if existingRevision == revision:
                    continue

        snapshot_download(repo_id=modelName, revision=revision, local_dir=modelDir)
        with versionFile.open("w") as outFile:
            outFile.write(revision)


class Model(Enum):
    HISTBERT = Path(settings.NER_BASE_DIR) / "checkpoints" / "crina-t_histbert-finetuned-ner"
    KB = Path(settings.NER_BASE_DIR) / "checkpoints" / "KBLab_bert-base-swedish-cased-ner"


def __getPipeline__(path: Path):
    tokenizer = AutoTokenizer.from_pretrained(path, truncation=True, padding=True, model_max_length=512)
    model = AutoModelForTokenClassification.from_pretrained(path)

    if torch.cuda.is_available():
        return pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="first", device="cuda")
    return pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="first")


def getHistbertPipeline():
    return __getPipeline__(Model.HISTBERT.value)


def getKBPipeline():
    return __getPipeline__(Model.KB.value)
