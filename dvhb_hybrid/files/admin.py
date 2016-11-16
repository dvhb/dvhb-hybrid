from django.contrib import admin
from . import models


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'uuid', 'image')
    exclude = ('uuid', )
