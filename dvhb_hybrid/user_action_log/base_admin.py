from django.contrib import admin
from django.urls import reverse, NoReverseMatch
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .enums import UserActionLogEntrySubType


class BaseUserActionLogEntryAdmin(admin.ModelAdmin):
    """
    Abstract action log entry admin class
    """
    date_hierarchy = 'created_at'

    list_display = [
        'created_at', 'user', 'ip_address', 'message', 'type', 'subtype', 'status', 'object_link'
    ]
    readonly_fields = [
        'created_at', 'user', 'ip_address', 'message', 'type', 'subtype', 'status', 'payload', 'content_type', 'object_id',
        'object_repr'
    ]
    list_filter = [
        'type',
        'subtype',
        'status',
        ('created_at', admin.DateFieldListFilter)
    ]
    search_fields = [
        'ip_address', 'message'
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

    def object_link(self, obj):
        ct = obj.content_type
        if ct is None:
            return
        # Fallback result (no reverse link found/object removed)
        link = escape(obj.object_repr)
        # Object has been removed
        if obj.subtype != UserActionLogEntrySubType.delete and obj.object_id is not None:
            try:
                link = mark_safe('<a href="%s">%s</a>' % (
                    reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                    escape(obj.object_repr),
                ))
            except NoReverseMatch:
                pass

        return link

    object_link.admin_order_field = 'object_repr'
    object_link.short_description = 'object'
