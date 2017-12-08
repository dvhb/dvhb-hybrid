# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-12-13 08:05
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0003_rename_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='images', to=settings.AUTH_USER_MODEL, verbose_name='Author'),
        ),
    ]