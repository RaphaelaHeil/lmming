from django.forms import ClearableFileInput, Form, FileField, CharField, ChoiceField, BooleanField, CheckboxInput, \
    MultipleChoiceField, CheckboxSelectMultiple, Textarea, DateField, DateInput, URLField, IntegerField, TextInput, \
    Select

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
    processName = CharField(max_length=100, label="Extraction Process Name:", required=True,
                            widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Name'}))
    file_field = MultipleFileField(label="Select transcription files (*.xml):")


class ProcessingStepForm(Form):

    def __init__(self, *args, **kwargs):
        super(ProcessingStepForm, self).__init__(*args, **kwargs)
        self.label = kwargs["initial"]["label"]
        self.tooltip = kwargs["initial"]["tooltip"]
        self.fields["mode"].initial = kwargs["initial"]["mode"]
        self.fields["mode"].disabled = kwargs["initial"]["modeDisabled"]
        self.fields["humanValidation"].initial = kwargs["initial"]["humanValidation"]

    mode = ChoiceField(choices=ProcessingStep.ProcessingStepMode, widget=Select(attrs={"class": "form-select"}))
    humanValidation = BooleanField(widget=CheckboxInput(attrs={'class': 'form-check-input'}), required=False)


class ZipForm(Form):
    zipFile = FileField(label="Select a compressed file, containing one or more collections (*.zip):",
                        widget=ClearableFileInput(attrs={"accept": ".zip", "class": "form-control"}))


class FileNameForm(Form):
    organisationID = CharField(label="Organisation ID", required=True,
                               widget=TextInput(attrs={'class': 'form-control'}))
    type = MultipleChoiceField(label="Report Type", choices=Report.DocumentType, required=True,
                               widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    date = CharField(label="Report date by year (comma-separted for multiple years)", required=True,
                     widget=TextInput(attrs={'class': 'form-control'}))


class FilemakerForm(Form):
    creator = CharField(label="Creator Name", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    relation = CharField(label="Relation (comma-separated)", required=False,
                         widget=TextInput(attrs={'class': 'form-control'}))
    coverage = ChoiceField(choices=Report.UnionLevel, required=True, widget=Select(attrs={"class": "form-select"}))
    spatial = CharField(label="Spatial (comma-separated)", required=True,
                        widget=TextInput(attrs={'class': 'form-control'}))


class ComputeForm(Form):
    title = CharField(label="Title", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    created = CharField(label="Year Created", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    available = DateField(label="Available from", required=False, input_formats=['%Y-%m-%d'],
                          widget=DateInput(format='%Y-%m-%d', attrs={"type": "date"}))
    accessRights = ChoiceField(choices=Report.AccessRights, required=True, label="Access Rights",
                               widget=Select(attrs={"class": "form-select"}))
    description = CharField(label="Report description", required=False,
                            widget=Textarea(attrs={"class": "form-control"}))
    language = CharField(label="Language (comma-separated)", required=True,
                         widget=TextInput(attrs={'class': 'form-control'}))
    license = CharField(label="License (comma-separated)", required=True,
                        widget=Textarea(attrs={'class': 'form-control'}))
    source = CharField(label="Source (comma-separated)", required=False,
                       widget=TextInput(attrs={'class': 'form-control'}))


class ArabGenerateForm(Form):
    title = CharField(label="Title", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    created = CharField(label="Year Created", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    available = DateField(label="Available from", required=False, input_formats=['%Y-%m-%d'],
                          widget=DateInput(format='%Y-%m-%d', attrs={"type": "date"}))
    accessRights = ChoiceField(choices=Report.AccessRights, required=True, label="Access Rights",
                               widget=Select(attrs={"class": "form-select"}))
    language = CharField(label="Language (comma-separated)", required=True,
                         widget=TextInput(attrs={'class': 'form-control'}))
    license = CharField(label="License (comma-separated)", required=True,
                        widget=Textarea(attrs={'class': 'form-control'}))
    source = CharField(label="Source (comma-separated)", required=False,
                       widget=TextInput(attrs={'class': 'form-control'}))
    isFormatOf = MultipleChoiceField(label="Format", choices=Report.DocumentFormat, required=True,
                                     widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))


class FacManualForm(Form):
    isVersionOf = URLField(label="Link to archival record (e.g. AtoM)", required=True, max_length=200,
                           widget=TextInput(attrs={'class': 'form-control'}))
    isFormatOf = MultipleChoiceField(label="Format", choices=Report.DocumentFormat, required=True,
                                     widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))


class ArabManualForm(Form):
    isVersionOf = URLField(label="Link to archival record (e.g. AtoM)", required=True, max_length=200,
                           widget=TextInput(attrs={'class': 'form-control'}))
    description = CharField(label="Report description", required=False,
                            widget=Textarea(attrs={"class": "form-control"}))


class MintForm(Form):
    # TODO: does this also update the pages? probably not ...
    identifier = URLField(label="IIIF URL", required=True, max_length=200,
                          widget=TextInput(attrs={'class': 'form-control'}))


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
    language = CharField(label="Default Language(s) (comma-separated)", required=True,
                         widget=TextInput(attrs={'class': 'form-control'}))
    license = CharField(label="Default License(s) (comma-separated)", required=True,
                        widget=TextInput(attrs={'class': 'form-control'}))
    source = CharField(label="Default Source(s) (comma-separated)", required=True,
                       widget=TextInput(attrs={'class': 'form-control'}))

    accessRights = ChoiceField(label="Default accessRights Value", choices=Report.AccessRights, required=True,
                               widget=Select(attrs={"class": "form-select"}))

    avilableYearOffset = IntegerField(label="Default number of years after publication", required=True, min_value=0,
                                      step_size=1)


class ExternalRecordsSettingsForm(Form):
    externalRecordCsv = FileField(label="External Record CSV",
                                  widget=ClearableFileInput(attrs={"accept": ".csv", "class": "form-control"}),
                                  required=False)
