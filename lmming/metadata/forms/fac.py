from django.forms import Form, CharField, TextInput, DateField, DateInput, ChoiceField, Select, Textarea, URLField, \
    MultipleChoiceField, CheckboxSelectMultiple

from metadata.i18n import SWEDISH
from metadata.models import Report


class ComputeForm(Form):
    title = CharField(label="Title [required]", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    created = CharField(label="Year Created [optional]", required=False,
                        widget=TextInput(attrs={'class': 'form-control'}))
    available = DateField(label="Available from [optional]", required=False, input_formats=['%Y-%m-%d'],
                          widget=DateInput(format='%Y-%m-%d', attrs={"type": "date"}))
    accessRights = ChoiceField(choices=Report.AccessRights, required=True, label="Access Rights [required]",
                               widget=Select(attrs={"class": "form-select"}))
    description = CharField(label="Report description [optional]", required=False,
                            widget=Textarea(attrs={"class": "form-control"}))
    language = CharField(label="Language (comma-separated) [required]", required=True,
                         widget=TextInput(attrs={'class': 'form-control'}))
    license = CharField(label="License (comma-separated) [required]", required=True,
                        widget=Textarea(attrs={'class': 'form-control'}))
    source = CharField(label="Source (comma-separated) [optional]", required=False,
                       widget=TextInput(attrs={'class': 'form-control'}))


class FacManualForm(Form):
    isFormatOf = MultipleChoiceField(label="Format [required]", choices=Report.DocumentFormat, required=True,
                                     widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    seriesVolumeName = CharField(label="Series Volume Name", required=False,
                                 widget=TextInput(attrs={'class': 'form-control'}))
    seriesVolumeSignum = CharField(label="Series Volume Signum", required=False,
                                   widget=TextInput(attrs={'class': 'form-control'}))


class MintForm(Form):
    identifier = URLField(label="ARK identifier URL [required]", required=True, max_length=200,
                          widget=TextInput(attrs={'class': 'form-control'}))


class FacFileNameForm(Form):
    organisationID = CharField(label="Organisation ID [required]", required=True,
                               widget=TextInput(attrs={'class': 'form-control'}))
    type = MultipleChoiceField(label="Report Type [required]", choices=Report.DocumentType, required=True,
                               widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    date = CharField(label="Report date by year (comma-separted for multiple years) [required]", required=True,
                     widget=TextInput(attrs={'class': 'form-control'}))


class TranslateForm(Form):
    coverageEN = CharField(label="English Coverage", disabled=True)
    coverage = ChoiceField(label="Coverage [required]", choices=((a, a) for a in SWEDISH.coverage.values()),
                           required=True, widget=Select(attrs={"class": "form-select"}))
    typeEN = CharField(label="English Report Type", disabled=True)
    type = MultipleChoiceField(label="Report Type [required]", choices=((a, a) for a in SWEDISH.type.values()),
                               required=True, widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    isFormatOfEN = CharField(label="English Format", disabled=True)
    isFormatOf = MultipleChoiceField(label="Format [required]", choices=((a, a) for a in SWEDISH.isFormatOf.values()),
                                     required=True, widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    accessRightsEN = CharField(label="English Access Rights", disabled=True)
    accessRights = ChoiceField(label="Access Rights [required]",
                               choices=((a, a) for a in SWEDISH.accessRights.values()), required=True,
                               widget=Select(attrs={"class": "form-select"}))
    descriptionEN = CharField(label="English Report Description", disabled=True)
    description = CharField(label="Report Description [optional]", required=False,
                            widget=Textarea(attrs={"class": "form-control"}))


class BatchFacManualForm(Form):
    def __init__(self, *args, **kwargs):
        self.reportId = kwargs["initial"]["reportId"]
        self.date = kwargs["initial"]["date"]
        self.title = kwargs["initial"]["title"]
        super(BatchFacManualForm, self).__init__(*args, **kwargs)  # call base class

    isFormatOf = MultipleChoiceField(label="Format [required]", choices=Report.DocumentFormat, required=True,
                                     widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    seriesVolumeName = CharField(label="Series Volume Name", required=False,
                                 widget=TextInput(attrs={'class': 'form-control'}))
    seriesVolumeSignum = CharField(label="Series Volume Signum", required=False,
                                   widget=TextInput(attrs={'class': 'form-control'}))
