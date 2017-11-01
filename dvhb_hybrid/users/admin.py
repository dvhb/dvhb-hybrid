from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import ugettext_lazy as _


class BaseUserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'picture')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
         ),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'picture')}),
    )

    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


class BaseUserConfirmationRequestAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'status')
    fields = ('uuid', 'email', 'status', 'created_at', 'user',)
    search_fields = ('email', 'name')
    ordering = ('-created_at',)

    list_filter = (
        'status',
        'created_at',
    )

    def get_readonly_fields(self, request, obj=None):
        fields = ['uuid', 'status', 'created_at', 'user']
        if obj:
            fields.append('email')
        return fields

    def has_add_permission(self, request):
        """
        Disables 'Add' button in admin
        """

        return False
