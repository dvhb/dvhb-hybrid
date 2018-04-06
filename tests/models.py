from django.db import models
from django.contrib.postgres.fields import JSONField
from dvhb_hybrid.users.models import AbstractUser

### For test_amodels

class Test(models.Model):
    id = models.IntegerField(primary_key=True)
    text = models.TextField()
    data = JSONField()


class User(AbstractUser):
    pass
