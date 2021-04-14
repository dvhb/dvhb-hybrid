# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-31 15:27
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mail_to', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=100), size=None)),
                ('subject', models.TextField()),
                ('body', models.TextField()),
                ('template', models.CharField(blank=True, max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('sent_at', models.DateTimeField(null=True)),
                ('attachments', models.JSONField(blank=True, default=dict, null=True)),
            ],
        ),
    ]
