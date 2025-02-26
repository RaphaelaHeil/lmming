from django.forms import Form, CharField, TextInput, Textarea, URLField, URLInput, ChoiceField, Select

from v2.forms.utils import MultipleFileField


class ProcessForm(Form):

    def __init__(self, *args, **kwargs):
        projects = kwargs.pop("projects")
        super(ProcessForm, self).__init__(*args, **kwargs)
        self.fields["project"].choices = [("", "-----------")] + projects

    name = CharField(required=True, widget=TextInput(attrs={'class': 'form-control'}))
    project = ChoiceField(choices=[("", "-----------")], widget=Select(attrs={"class": "form-select"}))
    file_field = MultipleFileField(label="Select files:")
