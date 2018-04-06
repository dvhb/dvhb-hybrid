from dvhb_hybrid.amodels import derive_from_django
from dvhb_hybrid.users.amodels import AbstractUser

from . import models


@derive_from_django(models.User)
class User(AbstractUser):
    pass
