# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-05-03 04:24
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0002_image_author'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='image',
            options={'ordering': ('-created_at',), 'verbose_name': 'image', 'verbose_name_plural': 'images'},
        ),
        migrations.AlterField(
            model_name='image',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to=settings.AUTH_USER_MODEL, verbose_name='Author'),
        ),
        migrations.AlterField(
            model_name='image',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, verbose_name='created at'),
        ),
        migrations.AlterField(
            model_name='image',
            name='meta',
            field=models.JSONField(blank=True, default=dict, verbose_name='meta-information'),
        ),
        migrations.AlterField(
            model_name='image',
            name='mime_type',
            field=models.CharField(blank=True, max_length=99, verbose_name='content type'),
        ),
        migrations.AlterField(
            model_name='image',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='update at'),
        ),
    ]
