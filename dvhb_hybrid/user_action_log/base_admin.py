from django.contrib import admin


class BaseUserActionLogEntryAdmin(admin.ModelAdmin):
    """
    Abstract action log entry admin class
    """

    list_display = [
        'created_at', 'user', 'ip_address', 'message', 'type', 'subtype'
    ]
    readonly_fields = [
        'created_at', 'user', 'ip_address', 'message', 'type', 'subtype'
    ]
    list_filter = [
        'type',
        'subtype',
        ('created_at', admin.DateFieldListFilter)
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
