from django.contrib import admin

from . import models


@admin.register(models.Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('uuid', 'image', 'created_at')
    exclude = ('uuid',)
    search_fields = ('uuid',)
    list_filter = ('author', 'mime_type')
    ordering = ('-created_at',)
