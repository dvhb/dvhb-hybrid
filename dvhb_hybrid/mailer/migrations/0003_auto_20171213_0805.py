# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-12-13 08:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('mailer', '0002_email_templates'),
    ]

    operations = [
        migrations.AlterField(
            model_name='templatetranslation',
            name='template',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='mailer.Template'),
        ),
    ]
