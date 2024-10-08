from django.forms import Form, CharField, TextInput, DateField, DateInput, ChoiceField, Select, Textarea, URLField, \
    MultipleChoiceField, CheckboxSelectMultiple

from metadata.models import Report


class ComputeForm(Form):
    title = CharField(label="Title [required]", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    created = CharField(label="Year Created [optional]", required=False, widget=TextInput(attrs={'class': 'form-control'}))
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


class MintForm(Form):
    # TODO: does this also update the pages? probably not ...
    identifier = URLField(label="IIIF URL [required]", required=True, max_length=200,
                          widget=TextInput(attrs={'class': 'form-control'}))


class FacFileNameForm(Form):
    organisationID = CharField(label="Organisation ID [required]", required=True,
                               widget=TextInput(attrs={'class': 'form-control'}))
    type = MultipleChoiceField(label="Report Type [required]", choices=Report.DocumentType, required=True,
                               widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    date = CharField(label="Report date by year (comma-separted for multiple years) [required]", required=True,
                     widget=TextInput(attrs={'class': 'form-control'}))
