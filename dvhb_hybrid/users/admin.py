from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.core.files.images import get_image_dimensions
from django.core.files.uploadedfile import UploadedFile
from django.forms import forms
from django.utils.translation import ugettext_lazy as _

from .models import AbstractUser


class UserForm(UserChangeForm):
    class Meta:
        model = AbstractUser
        fields = '__all__'

    def clean_picture(self):
        """
        Implements validation of new user picture uploaded
        """

        picture = self.cleaned_data.get('picture')

        # New picture has been uploaded
        if picture and isinstance(picture, UploadedFile):
            # Validate content type
            main, sub = picture.content_type.split('/')
            if not (main == 'image' and sub in ['jpeg', 'pjpeg', 'gif', 'png']):
                raise forms.ValidationError(
                    _('Please use a JPEG, GIF or PNG image.'))

            w, h = get_image_dimensions(picture)

            # Validate picture dimensions
            max_width = max_height = 1024
            if w > max_width or h > max_height:
                raise forms.ValidationError(
                    _('Please use an image that is %sx%s pixels or smaller.' % (max_width, max_height)))

            # Validate file size
            if len(picture) > (500 * 1024):
                raise forms.ValidationError(
                    _('User picture size may not exceed 500 kB.'))

        return picture


class BaseUserAdmin(DjangoUserAdmin):
    form = UserForm
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')}
         ),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
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
