from dvhb_hybrid.amodels import Model

from .models import User as DjangoUser

class User(Model):
    table = Model.get_table_from_django(DjangoUser)
