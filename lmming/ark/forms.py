from django.forms import Form, CharField, TextInput, URLInput, URLField, HiddenInput, ChoiceField, Select

from ark.utils import FAC_SHOULDERS


class ArkDetails(Form):
    ark = URLField(max_length=200, label="ARK", required=True,
                   widget=URLInput(attrs={'class': 'form-control',
                                          'placeholder': 'Full ARK URL, e.g. https://ark.fauppsala.se/ark:/30441/test12345'}))


class EditArk(Form):
    ark = CharField(max_length=200, required=False, widget=HiddenInput())
    url = URLField(max_length=200, label="URL [required]", required=True,
                   widget=URLInput(attrs={'class': 'form-control',
                                          'placeholder': 'Full URL that the ARK should point to'}))
    title = CharField(max_length=200, required=False, label="Title",
                      widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'DC Terms Title'}))
    type = CharField(max_length=200, required=False, label="Type",
                     widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'DC Terms Type'}))
    commitment = CharField(max_length=200, required=False, label="Commitment",
                           widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Commitment'}))
    identifier = CharField(max_length=200, required=False, label="Identifier",
                           widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'DC Terms Identifier'}))
    format = CharField(max_length=200, required=False, label="Format",
                       widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'DC Terms Format'}))
    relation = CharField(max_length=200, label="Relation", required=False,
                         widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'DC Terms Relation'}))
    source = URLField(max_length=200, label="Source [URL format]", required=False,
                      widget=URLInput(attrs={'class': 'form-control', 'placeholder': 'DC Terms Source'}))
    metadata = CharField(max_length=200, required=False, label="Metadata",
                         widget=TextInput(attrs={'class': 'form-control', 'placeholder': 'Miscellaneous Metadata'}))


class CreateArk(EditArk):
    shoulder = ChoiceField(label="Shoulder (=ARK type) [required]", required=True,
                           widget=Select(attrs={"class": "form-select",
                                                'placeholder': 'Shoulder under which the ARK should be created'}),
                           choices=FAC_SHOULDERS)

    field_order = ['shoulder']
