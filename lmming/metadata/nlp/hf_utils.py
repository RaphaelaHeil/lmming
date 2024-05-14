from enum import Enum
from pathlib import Path

from django.conf import settings
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch
from huggingface_hub import hf_hub_download, snapshot_download


def download():
    for modelName in ["crina-t/histbert-finetuned-ner", "KBLab/bert-base-swedish-cased-ner"]:
        snapshot_download(repo_id=modelName,
                          local_dir=settings.NER_BASE_DIR / "checkpoints" / modelName.replace("/", "_"))


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
