from django.db import models
from .auth import ForceAPI


class Query(models.Model):
    name = models.CharField(
        max_length=80)
    soql = models.TextField(
        null=True,
        blank=True)
    api = models.ForeignKey(
        ForceAPI,
        on_delete=models.CASCADE)

    def __str__(self):
        return self.name
