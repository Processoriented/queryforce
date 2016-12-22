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
    operator = forms.ChoiceField(
        choices=OPERATOR_CHOICES,
        label="")
    value = forms.CharField(
        max_length=255,
        label="")

    def apply_filter(self):
        pass

