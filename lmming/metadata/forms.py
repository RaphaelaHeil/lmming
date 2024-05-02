from django.forms import ClearableFileInput, Form, FileField, CharField, ChoiceField, BooleanField, CheckboxInput, \
    MultipleChoiceField, CheckboxSelectMultiple, Textarea
from metadata.models import ProcessingStep, Report


class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"accept": ".xml", "class": "form-control"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class ExtractionTransferDetailForm(Form):
    processName = CharField(max_length=100, label="Extraction Process Name:", required=True)
    file_field = MultipleFileField(label="Select transcription files (*.xml):")


class ExtractionTransferSettingsForm(Form):
    filenameMode = ChoiceField(choices=ProcessingStep.ProcessingStepMode.choices,
                               initial=ProcessingStep.ProcessingStepMode.AUTOMATIC)
    filenameHumVal = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}),
                                  required=False)
    filemakerMode = ChoiceField(choices=ProcessingStep.ProcessingStepMode.choices,
                                initial=ProcessingStep.ProcessingStepMode.AUTOMATIC)
    filemakerHumVal = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}),
                                   required=False)
    generateMode = ChoiceField(choices=ProcessingStep.ProcessingStepMode.choices,
                               initial=ProcessingStep.ProcessingStepMode.AUTOMATIC)
    generateHumVal = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}),
                                  required=False)
    imageMode = ChoiceField(choices=ProcessingStep.ProcessingStepMode.choices,
                            initial=ProcessingStep.ProcessingStepMode.MANUAL, disabled=True)
    imageHumVal = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}), required=False,
                               disabled=True)
    nerMode = ChoiceField(choices=ProcessingStep.ProcessingStepMode.choices,
                          initial=ProcessingStep.ProcessingStepMode.AUTOMATIC)
    nerHumVal = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}), required=False)
    mintMode = ChoiceField(choices=ProcessingStep.ProcessingStepMode.choices,
                           initial=ProcessingStep.ProcessingStepMode.AUTOMATIC)
    mintHumVal = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}), required=False)


class ZipForm(Form):
    zipFile = FileField(label="Select a compressed file, containing one or more collections (*.zip):",
                        widget=ClearableFileInput(attrs={"accept": ".zip", "class": "form-control"}))


class FileNameForm(Form):
    organisationID = CharField(label="Organisation ID", required=True)
    type = MultipleChoiceField(label="Report Type", choices=Report.DocumentType, required=True,
                               widget=CheckboxSelectMultiple)
    date = CharField(label="Report date by year (comma-separted for multiple years)", required=True)


class FilemakerForm(Form):
    creator = CharField(label="Creator Name", required=True)
    relation = CharField(label="Relation (comma-separated)", required=False)
    coverage = ChoiceField(choices=Report.UnionLevel, required=True)
    spatial = CharField(label="Spatial (comma-separated)", required=True)
