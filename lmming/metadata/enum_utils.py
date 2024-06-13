from enum import Enum


class PipelineStepName(Enum):
    FILENAME = 10, "Filename-based extraction"
    FILEMAKER_LOOKUP = 20, "Lookup in Filemaker export"
    GENERATE = 30, "Generate/Calculate"
    FAC_MANUAL = 35, "Manual"
    IMAGE = 40, "Image-based extraction"
    NER = 50, "Named Entity Recognition"
    MINT_ARKS = 60, "Mint ARKs"
