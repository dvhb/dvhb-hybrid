# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-09 09:55
from __future__ import unicode_literals

from django.db import migrations, models
import dvhb_hybrid.files.storages


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Image',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Дата обновления')),
                ('uuid', models.UUIDField(primary_key=True, serialize=False, verbose_name='UUID')),
                ('image', dvhb_hybrid.models.SVGAndImageField(
                    storage=dvhb_hybrid.files.storages.ImageStorage(),
                    upload_to=''
                )),
                ('mime_type', models.CharField(blank=True, max_length=99, verbose_name='тип содежимого')),
                ('meta', models.JSONField(blank=True, default={}, verbose_name='мета-информация')),
            ],
            options={
                'verbose_name_plural': 'Изображения',
                'ordering': ('-created_at',),
                'verbose_name': 'изображение',
            },
        ),
    ]
