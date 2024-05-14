import datetime

from django.forms import ClearableFileInput, Form, FileField, CharField, ChoiceField, BooleanField, CheckboxInput, \
    MultipleChoiceField, CheckboxSelectMultiple, Textarea, DateField, DateInput, URLField, IntegerField
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


class ComputeForm(Form):
    title = CharField(label="Title", required=True)
    created = CharField(label="Year Created", required=False)
    available = DateField(label="Available from", required=False, input_formats=['%Y-%m-%d'],
                          widget=DateInput(format='%Y-%m-%d', attrs={"type": "date"}))
    accessRights = ChoiceField(choices=Report.AccessRights, required=True)
    description = CharField(label="Report description", required=False, widget=Textarea())
    language = CharField(label="Language (comma-separated)", required=True)
    license = CharField(label="License (comma-separated)", required=True, widget=Textarea())
    source = CharField(label="Source (comma-separated)", required=False)


class ImageForm(Form):
    isFormatOf = MultipleChoiceField(label="Format", choices=Report.DocumentFormat, required=True,
                        widget=CheckboxSelectMultiple)

class MintForm(Form):
    identifier = URLField(label="IIIF URL", required=True)
    isVersionOf = URLField(label="Link to archival record (e.g. AtoM)", required=True)


class PageForm(Form):
    def __init__(self, *args, **kwargs):
        self.pageId = kwargs["initial"]["pageId"]
        self.order = kwargs["initial"]["order"]
        super(PageForm, self).__init__(*args, **kwargs)  # call base class

    # pageId = CharField(widget=HiddenInput(), required=False)
    measures = BooleanField(initial=False, widget=CheckboxInput(attrs={'class': 'form-check-input'}), required=False)
    transcription = CharField(label="Transcription", required=False,
                              widget=Textarea(attrs={"class": "form-control", "rows": 10}))
    normalisedTranscription = CharField(label="Normalised transcription", required=False,
                                        widget=Textarea(attrs={"class": "form-control", "rows": 10}))
    persons = CharField(label="Persons", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 3}))
    organisations = CharField(label="Organisations", required=False,
                              widget=Textarea(attrs={"class": "form-control", "rows": 3}))
    locations = CharField(label="Locations", required=False,
                          widget=Textarea(attrs={"class": "form-control", "rows": 3}))
    times = CharField(label="Times", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 3}))
    works = CharField(label="Works", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 3}))
    events = CharField(label="Events", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 3}))
    ner_objects = CharField(label="Objects", required=False,
                            widget=Textarea(attrs={"class": "form-control", "rows": 3}))


class SettingsForm(Form):
    iiifURL = URLField(label="IIIF Base-URL", required=True)
    atomURL = URLField(label="Base-URL to archival record system (e.g. AtoM)", required=True)

    language = CharField(label="Default Language(s) (comma-separated)", required=True)
    license = CharField(label="Default License(s) (comma-separated)", required=True)
    source = CharField(label="Default Source(s) (comma-separated)", required=True)

    accessRights = ChoiceField(label="Default accessRights Value", choices=Report.AccessRights, required=True)

    avilableYearOffset = IntegerField(label="Default number of years after publication", required=True, min_value=0,
                                      step_size=1)


class FilemakerSettingsForm(Form):
    filemaker_csv = FileField(label="Filemaker CSV",
                              widget=ClearableFileInput(attrs={"accept": ".csv", "class": "form-control"}))
