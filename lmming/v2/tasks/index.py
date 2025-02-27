from v2.tasks import nlp, handles, generate, fill

STEP_INDEX = {"extractText": nlp.extractText,
              "generateValues": generate.generateValues,
              # "ner":nlp.ner,
              "createIIIFHandles": handles.createIIIFHandles,
              "fillFromExternalRecords": fill.fillFromExternalRecords,
              "fillFixedValues": fill.fillFixedValues
              }
