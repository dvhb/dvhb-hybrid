from django import forms
from django.contrib import admin

from .models import Template, TemplateTranslation


class TemplateAdminForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(),
        }


class TemplateTranslationAdminForm(forms.ModelForm):
    class Meta:
        model = TemplateTranslation
        fields = '__all__'
        widgets = {
            'message_body': forms.Textarea(),
        }


class TemplateTranslationInline(admin.StackedInline):
    model = TemplateTranslation
    form = TemplateTranslationAdminForm
    extra = 1


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    inlines = [TemplateTranslationInline]
    form = TemplateAdminForm

    search_fields = ['name', 'description']
    list_display = ['name', 'description', 'updated_at']
    list_filter = ['updated_at']
    ordering = ['name']


@admin.register(TemplateTranslation)
class TemplateTranslationAdmin(admin.ModelAdmin):
    form = TemplateTranslationAdminForm
    search_fields = ['name', 'description']
    list_display = ['template', 'language', 'lang_code', 'message_subject', 'updated_at']
    list_filter = ['template', 'lang_code', 'updated_at']
    ordering = ['template']
