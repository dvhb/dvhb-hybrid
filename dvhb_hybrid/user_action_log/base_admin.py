from django.contrib import admin
from django.urls import reverse
from django.utils.html import escape
from .enums import UserActionLogEntrySubType


class BaseUserActionLogEntryAdmin(admin.ModelAdmin):
    """
    Abstract action log entry admin class
    """
    date_hierarchy = 'created_at'

    list_display = [
        'created_at', 'user', 'ip_address', 'message', 'type', 'subtype', 'object_link'
    ]
    readonly_fields = [
        'created_at', 'user', 'ip_address', 'message', 'type', 'subtype', 'payload', 'content_type', 'object_id',
        'object_repr'
    ]
    list_filter = [
        'type',
        'subtype',
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
        # Object has been removed
        if obj.subtype == UserActionLogEntrySubType.delete:
            link = escape(obj.object_repr)
        else:
            if obj.object_id is None:
                return
            link = u'<a href="%s">%s</a>' % (
                reverse('admin:%s_%s_change' % (ct.app_label, ct.model), args=[obj.object_id]),
                escape(obj.object_repr),
            )
        return link

    object_link.allow_tags = True
    object_link.admin_order_field = 'object_repr'
    object_link.short_description = u'object'
