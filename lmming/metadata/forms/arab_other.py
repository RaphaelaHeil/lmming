from django.forms import Form, CharField, TextInput, ChoiceField, Select, Textarea, \
    URLField

from metadata.models import Report


class ArabOtherManualForm(Form):
    title = CharField(label="Titel [obligatorisk]", required=True, widget=TextInput(attrs={'class': 'form-control'}))
    source = CharField(label="Referenskod [obligatorisk]", required=True,
                       widget=TextInput(attrs={'class': 'form-control'}))
    description = CharField(label="Beskrivning", required=False, widget=Textarea(attrs={"class": "form-control"}))
    date = CharField(label="Omfattar tid (kommaseparerad lista)", required=True,
                     widget=TextInput(attrs={'class': 'form-control'}))
    created = CharField(label="Publicerat datum", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    format = CharField(label="Materialtyp", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    accessRights = ChoiceField(choices=Report.AccessRights, required=False, label="Access Rights [required]",
                               widget=Select(attrs={"class": "form-select"}))
    license = CharField(label="Upphovsrätt", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    comment = CharField(label="Anmärkning", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    spatial = CharField(label="Topografi", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    medium = CharField(label="Originalformat", required=False, widget=TextInput(attrs={'class': 'form-control'}))
    language = CharField(label="Språk", required=False, widget=TextInput(attrs={'class': 'form-control'}))


class ArabOtherMintForm(Form):
    identifier = URLField(label="IIIF Handle [obligatorisk]", required=True, max_length=200,
                          widget=TextInput(attrs={'class': 'form-control'}))


class ArabOtherFileNameForm(Form):
    organisationID = CharField(label="Arkiv ID [obligatorisk]", required=True,
                               widget=TextInput(attrs={'class': 'form-control'}))
    typeName = CharField(label="Handlingstyp", required=True, widget=TextInput(attrs={'class': 'form-control'}))


class ArabOtherFilemakerForm(Form):
    creator = CharField(label="Arkiv [obligatorisk]", required=False, widget=TextInput(attrs={'class': 'form-control'}))
