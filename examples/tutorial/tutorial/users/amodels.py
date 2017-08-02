from dvhb_hybrid.amodels import Model

from .models import User as DjangoUser


class User(Model):
    # Build sqlalchemy model by Django model
    table = Model.get_table_from_django(DjangoUser)
