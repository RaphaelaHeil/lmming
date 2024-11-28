from django.forms import Form, CharField, TextInput, URLInput, URLField, HiddenInput


class ArkDetails(Form):
    ark = URLField(max_length=200, label="ARK", required=True,
                   widget=URLInput(attrs={'class': 'form-control',
                                          'placeholder': 'Full ARK URL, e.g. https://ark.fauppsala.se/ark:/30441/test12345'}))


class EditArk(Form):
    ark = CharField(max_length=200, required=False, widget=HiddenInput())
    url = URLField(max_length=200, label="URL", required=True,
                   widget=URLInput(attrs={'class': 'form-control',
                                          'placeholder': 'Full URL that the ARK should point to'}))
    title = CharField(max_length=200, required=False, label="Title", widget=TextInput(attrs={'class': 'form-control'}))
    type = CharField(max_length=200, required=False, label="Type", widget=TextInput(attrs={'class': 'form-control'}))
    commitment = CharField(max_length=200, required=False, label="Commitment",
                           widget=TextInput(attrs={'class': 'form-control'}))
    identifier = CharField(max_length=200, required=False, label="Identifier",
                           widget=TextInput(attrs={'class': 'form-control'}))
    format = CharField(max_length=200, required=False, label="Format",
                       widget=TextInput(attrs={'class': 'form-control'}))
    relation = URLField(max_length=200, label="Relation", required=False,
                        widget=URLInput(attrs={'class': 'form-control', 'placeholder': 'URL to Relation '}))
    source = URLField(max_length=200, label="Source", required=False,
                      widget=URLInput(attrs={'class': 'form-control', 'placeholder': 'URL to Source'}))
    metadata = CharField(max_length=200, required=False, label="Metadata",
                         widget=TextInput(attrs={'class': 'form-control'}))
