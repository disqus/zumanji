from django import forms


class UploadJsonForm(forms.Form):
    revision = forms.CharField(max_length=64, required=False,
        help_text="(Optional) Specify a revision for this build. We will try to extract this from the JSON file if not specified.")
    json_file = forms.FileField()
