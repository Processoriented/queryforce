from django import forms
from .models import Query, DisplayColumn


class QueryForm(forms.ModelForm):
    """docstring for QueryForm"""

    class Meta:
        model = Query
        fields = ('name', 'soql', 'api',)
