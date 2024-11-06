from django.forms import Form, CharField, TextInput, DateField, DateInput, ChoiceField, Select, Textarea, \
    MultipleChoiceField, CheckboxSelectMultiple, URLField

from metadata.i18n import SWEDISH
from metadata.models import Report


class ArabGenerateForm(Form):
    title = CharField(label="Title [required]", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    created = CharField(label="Year Created [optional]", required=False,
                        widget=TextInput(attrs={'class': 'form-control'}))
    available = DateField(label="Available from [optional]", required=False, input_formats=['%Y-%m-%d'],
                          widget=DateInput(format='%Y-%m-%d', attrs={"type": "date"}))
    accessRights = ChoiceField(choices=Report.AccessRights, required=True, label="Access Rights [required]",
                               widget=Select(attrs={"class": "form-select"}))
    language = CharField(label="Language (comma-separated) [required]", required=True,
                         widget=TextInput(attrs={'class': 'form-control'}))
    license = CharField(label="License (comma-separated) [required]", required=True,
                        widget=Textarea(attrs={'class': 'form-control'}))
    source = CharField(label="Source (comma-separated) [optional]", required=False,
                       widget=TextInput(attrs={'class': 'form-control'}))
    isFormatOf = MultipleChoiceField(label="Format [required]", choices=Report.DocumentFormat, required=True,
                                     widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))


class ArabManualForm(Form):
    title = CharField(label="Title [required]", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    reportType = MultipleChoiceField(label="Report Type [required]", choices=Report.DocumentType, required=True,
                                     widget=CheckboxSelectMultiple(attrs={"class": "form-check-input"}))
    description = CharField(label="Report description [optional]", required=False,
                            widget=Textarea(attrs={"class": "form-control"}))
    descriptionSv = CharField(label="Swedish report description [optional]", required=False,
                              widget=Textarea(attrs={"class": "form-control"}))


class ArabMintForm(Form):
    identifier = URLField(label="Handle identifier URL [required]", required=True, max_length=200,
                          widget=TextInput(attrs={'class': 'form-control'}))


class ArabFileNameForm(Form):
    organisationID = CharField(label="Organisation ID [required]", required=True,
                               widget=TextInput(attrs={'class': 'form-control'}))
    date = CharField(label="Report date by year (comma-separted for multiple years) [required]", required=True,
                     widget=TextInput(attrs={'class': 'form-control'}))


class ArabTranslateForm(Form):
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
