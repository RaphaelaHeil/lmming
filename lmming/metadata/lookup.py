from metadata.models import ProcessingStep

URL_STEP_INDEX = {ProcessingStep.ProcessingStepType.FILENAME: "filename",
                  ProcessingStep.ProcessingStepType.FILEMAKER_LOOKUP: "filemaker",
                  ProcessingStep.ProcessingStepType.GENERATE: "generate",
                  ProcessingStep.ProcessingStepType.IMAGE: "image",
                  ProcessingStep.ProcessingStepType.NER: "ner",
                  ProcessingStep.ProcessingStepType.MINT_ARKS: "mint",
                  ProcessingStep.ProcessingStepType.FAC_MANUAL: "fac_manual",
                  }
