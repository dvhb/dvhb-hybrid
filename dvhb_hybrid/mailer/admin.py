from django.contrib import admin
from . import models


@admin.register(models.Message)
class MessageAdmin(admin.ModelAdmin):
    search_fields = ('subject', 'body', 'mail_to')
    date_hierarchy = 'created_at'
    list_display = (
        'pk', 'mail_to', 'subject',
        'created_at', 'sent_at',
        'template',
    )
    readonly_fields = (
        'pk', 'mail_to',
        'created_at', 'sent_at',
        'template',
        'subject',
        'body',
    )
