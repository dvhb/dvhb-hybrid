from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from dvhb_hybrid.models import CreatedMixin


class ExampleModel(models.Model):
    text = models.TextField()
    data = models.JSONField()


class MPTTTestModel(CreatedMixin, MPTTModel):
    name = models.CharField(max_length=255, null=True, blank=True)
    parent = TreeForeignKey('self', on_delete=models.CASCADE, null=True, blank=True)

    class MPTTMeta:
        order_insertion_by = ['name']
