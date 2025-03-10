from django.forms import ClearableFileInput, FileField, Form, CharField, TextInput, ChoiceField, Select, BooleanField, \
    CheckboxInput, Textarea, IntegerField, URLField, FileInput
from torch.optim.optimizer import required

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
    handlerName = CharField(label="Handler Name", required=False,
                            widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Archivist'}))
    file_field = MultipleFileField(label="Select transcription files (*.xml):")


class TransferImportForm(Form):
    processName = CharField(max_length=100, label="Extraction Process Name:", required=True,
                            widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Name'}))
    handlerName = CharField(label="Handler Name", required=False,
                            widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Archivist'}))
    transcriptionFiles = MultipleFileField(label="Select (unrestricted!) transcription files (*.xml):", required=True)
    itemsFile = FileField(label="items.csv (unrestricted!)", required=True,
                          widget=FileInput(attrs={"accept": ".csv", "class": "form-control"}))
    mediaFile = FileField(label="media.csv (unrestricted!)", required=True,
                          widget=FileInput(attrs={"accept": ".csv", "class": "form-control"}))
    structMapFile = FileField(label="mets_structmap.xml (unrestricted!)", required=True,
                              widget=FileInput(attrs={"accept": ".xml", "class": "form-control"}))


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


class FilemakerForm(Form):
    creator = CharField(label="Creator Name [required]", required=True,
                        widget=TextInput(attrs={'class': 'form-control'}))
    relation = CharField(label="Relation (comma-separated)", required=False,
                         widget=TextInput(attrs={'class': 'form-control'}))
    coverage = ChoiceField(label="Coverage [required]", choices=Report.UnionLevel, required=True,
                           widget=Select(attrs={"class": "form-select"}))
    spatial = CharField(label="Spatial (comma-separated) [required]", required=True,
                        widget=TextInput(attrs={'class': 'form-control'}))
    isVersionOf = URLField(label="Link to archival record (e.g. AtoM) [required]", required=True, max_length=200,
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
    persons = CharField(label="Persons", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 10}))
    organisations = CharField(label="Organisations", required=False,
                              widget=Textarea(attrs={"class": "form-control", "rows": 10}))
    locations = CharField(label="Locations", required=False,
                          widget=Textarea(attrs={"class": "form-control", "rows": 10}))
    times = CharField(label="Times", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 10}))
    works = CharField(label="Works", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 5}))
    events = CharField(label="Events", required=False, widget=Textarea(attrs={"class": "form-control", "rows": 5}))
    ner_objects = CharField(label="Objects", required=False,
                            widget=Textarea(attrs={"class": "form-control", "rows": 5}))


class SettingsForm(Form):
    language = CharField(label="Default Language(s) (comma-separated) [required]", required=True,
                         widget=TextInput(attrs={'class': 'form-control'}))
    license = CharField(label="Default License(s) (comma-separated) [required]", required=True,
                        widget=TextInput(attrs={'class': 'form-control'}))
    source = CharField(label="Default Source(s) (comma-separated) [required]", required=True,
                       widget=TextInput(attrs={'class': 'form-control'}))

    avilableYearOffset = IntegerField(label="Default number of years after publication [required]", required=True,
                                      min_value=0, step_size=1)
    normalisationYearCutOff = IntegerField(
        label="Final year to apply spelling normalisations (no normalisations after given year) [required]",
        required=True,
        min_value=0, step_size=1, initial=1910)


class ExternalRecordsSettingsForm(Form):
    externalRecordCsv = FileField(label="External Record CSV",
                                  widget=ClearableFileInput(attrs={"accept": ".csv", "class": "form-control"}),
                                  required=False)


class BatchPageHandleForm(Form):
    def __init__(self, *args, **kwargs):
        self.pageId = kwargs["initial"]["pageId"]
        self.filename = kwargs["initial"]["filename"]
        super(BatchPageHandleForm, self).__init__(*args, **kwargs)

    identifier = CharField(label="Identifier [mandatory]", required=True,
                           widget=TextInput(attrs={'class': 'form-control'}))
    source = CharField(label="Source [optional]", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    bibCitation = CharField(label="Bibliographic Citation [optional]", required=False,
                            widget=Textarea(attrs={'class': 'form-control', 'rows': 5}))
