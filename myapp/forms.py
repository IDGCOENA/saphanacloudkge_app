from django import forms
 
class VideoForm(forms.Form):
    prompt = forms.CharField(label='Prompt', max_length=5000)