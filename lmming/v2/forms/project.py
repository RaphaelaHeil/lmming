from django.forms import Form, CharField, TextInput, Textarea, URLField, URLInput


class ProjectForm(Form):
    name = CharField(required=True, widget=TextInput(attrs={'class': 'form-control'}))
    abbreviation = CharField(required=True, max_length=6, widget=TextInput(attrs={'class': 'form-control'}))
    description = CharField(required=False, widget=Textarea(attrs={"class": "form-control", "rows": 5}))
    recordIdColumnName = CharField(required=False, widget=TextInput(attrs={'class': 'form-control'}))
    externalRecordColumnNames = CharField(required=False, widget=Textarea(attrs={"class": "form-control", "rows": 5}))
