from django import forms

class ParseForm(forms.Form):
    parsefile = forms.FileField(
        label='Select a file',
        help_text='max. 42 megabytes'
    )