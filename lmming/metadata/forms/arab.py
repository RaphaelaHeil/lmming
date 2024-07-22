from django.forms import Form, CharField, TextInput, DateField, DateInput, ChoiceField, Select, Textarea, \
    MultipleChoiceField, CheckboxSelectMultiple, URLField

from metadata.models import Report


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


class ArabManualForm(Form):
    isVersionOf = URLField(label="Link to archival record (e.g. AtoM)", required=True, max_length=200,
                           widget=TextInput(attrs={'class': 'form-control'}))
    description = CharField(label="Report description", required=False,
                            widget=Textarea(attrs={"class": "form-control"}))
