from django.forms import Form, CharField, TextInput, Textarea, URLField, \
    URLInput


class VocabularyForm(Form):
    name = CharField(required=True, widget=TextInput(attrs={'class': 'form-control'}))
    description = CharField(required=False, widget=Textarea(attrs={"class": "form-control", "rows":5}))
    url = URLField(required=False, widget=URLInput(attrs={'class': 'form-control'}))


class MetadataTermForm(Form):

    def __init__(self, *args, **kwargs):
        if "initial" in kwargs and "id" in kwargs["initial"]:
            self.id = kwargs["initial"]["id"]
        else:
            self.id = -1
        super(MetadataTermForm, self).__init__(*args, **kwargs)  # call base class

    standardTerm = CharField(required=True, widget=TextInput(attrs={'class': 'form-control', 'required': 'required'}))
    description = CharField(required=False, widget=Textarea(attrs={"class": "form-control", "rows":3}))


class ProjectForm(Form):
    name = CharField(required=True, widget=TextInput(attrs={'class': 'form-control'}))
    abbreviation = CharField(required=True, max_length=6, widget=TextInput(attrs={'class': 'form-control'}))
    recordIdColumnName = CharField(required=True, widget=Textarea(attrs={"class": "form-control"}))
    description = CharField(required=False, widget=Textarea(attrs={"class": "form-control"}))
