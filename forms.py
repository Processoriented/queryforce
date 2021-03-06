from django import forms
from .models import Query, DisplayColumn


class QueryForm(forms.ModelForm):
    """docstring for QueryForm"""

    class Meta:
        model = Query
        fields = ('name', 'soql', 'api',)

class ParameterForm(forms.Form):
    OPERATOR_CHOICES = (
        ('=', '='),
        ('!=', '!='),
        ('<', '<'),
        ('<=', '<='),
        ('>', '>'),
        ('>=', '>='),
        ('in', 'in'),
        ('not in', 'not in'),
        ('starts with', 'starts with'),
        ('ends with', 'ends with'),
        ('contains', 'contains'),
    )

    def __init__(self, *args, **kwargs):
        query_id = kwargs['initial'].pop('query_pk', 0)
        self.query_pk = query_id
        param_name = kwargs['initial'].pop('parameter', None)
        self.parameter = param_name
        super(ParameterForm, self).__init__(*args, **kwargs)

        self.fields['query'] = forms.IntegerField(
            label="",
            widget=forms.HiddenInput(attrs={
                'value': query_id}))
        self.fields['parameter'] = forms.CharField(
            max_length=80,
            initial=self.parameter,
            label="",
            widget=forms.TextInput(attrs={
                'value': self.parameter,
                'readonly': True,
                'class': 'form-control'
                }))
        self.fields['operator'] = forms.ChoiceField(
            choices=self.OPERATOR_CHOICES,
            label="",
            widget=forms.Select(attrs={
                'class': 'form-control'
                }))
        self.fields['value'] = forms.CharField(
            max_length=255,
            label="",
            widget=forms.TextInput(attrs={
                'class': 'form-control'
                }))
        # self.fields['operator'].label = param_name

    def apply_filter(self):
        pass
