# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-06-05 09:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gvsigol_symbology', '0002_textsymbolizer_is_actived'),
    ]

    operations = [
        migrations.AddField(
            model_name='style',
            name='maxscale',
            field=models.FloatField(blank=True, default=-1, null=True),
        ),
        migrations.AddField(
            model_name='style',
            name='minscale',
            field=models.FloatField(blank=True, default=-1, null=True),
        ),
    ]