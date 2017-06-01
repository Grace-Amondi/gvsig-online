# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2017-05-31 10:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('gvsigol_services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ColorMap',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(max_length=100)),
                ('extended', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='ColorMapEntry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=0)),
                ('color', models.CharField(max_length=100)),
                ('quantity', models.FloatField()),
                ('label', models.CharField(max_length=100)),
                ('opacity', models.FloatField(default=1.0)),
                ('color_map', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.ColorMap')),
            ],
        ),
        migrations.CreateModel(
            name='Library',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=500, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='LibraryRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('library', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.Library')),
            ],
        ),
        migrations.CreateModel(
            name='Rule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('title', models.CharField(blank=True, max_length=500, null=True)),
                ('abstract', models.CharField(blank=True, max_length=500, null=True)),
                ('filter', models.CharField(blank=True, max_length=5000, null=True)),
                ('minscale', models.FloatField(blank=True, default=-1, null=True)),
                ('maxscale', models.FloatField(blank=True, default=-1, null=True)),
                ('order', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Style',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('title', models.CharField(blank=True, max_length=100, null=True)),
                ('is_default', models.BooleanField(default=False)),
                ('type', models.CharField(choices=[('US', 'S\xedmbolo \xfanico'), ('UV', 'Valores \xfanicos'), ('IN', 'Intervalos'), ('EX', 'Expresiones'), ('CT', 'Tabla de color'), ('CH', 'Gr\xe1ficas')], default='US', max_length=2)),
                ('order', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='StyleLayer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_services.Layer')),
                ('style', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.Style')),
            ],
        ),
        migrations.CreateModel(
            name='Symbolizer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='ExternalGraphicSymbolizer',
            fields=[
                ('symbolizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='gvsigol_symbology.Symbolizer')),
                ('opacity', models.IntegerField(default=1)),
                ('size', models.IntegerField(default=8)),
                ('rotation', models.IntegerField(default=0)),
                ('online_resource', models.CharField(max_length=1000)),
                ('format', models.CharField(max_length=100)),
            ],
            bases=('gvsigol_symbology.symbolizer',),
        ),
        migrations.CreateModel(
            name='LineSymbolizer',
            fields=[
                ('symbolizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='gvsigol_symbology.Symbolizer')),
                ('stroke', models.CharField(max_length=100)),
                ('stroke_width', models.IntegerField(default=1)),
                ('stroke_opacity', models.FloatField(default=1.0)),
            ],
            bases=('gvsigol_symbology.symbolizer',),
        ),
        migrations.CreateModel(
            name='MarkSymbolizer',
            fields=[
                ('symbolizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='gvsigol_symbology.Symbolizer')),
                ('opacity', models.IntegerField(default=1)),
                ('size', models.IntegerField(default=8)),
                ('rotation', models.IntegerField(default=0)),
                ('well_known_name', models.CharField(choices=[('circle', 'C\xedrculo'), ('square', 'Cuadrado'), ('triangle', 'Tri\xe1ngulo'), ('star', 'Estrella'), ('cross', 'Cruz')], default='circle', max_length=25)),
                ('fill', models.CharField(max_length=100)),
                ('fill_opacity', models.FloatField(default=1.0)),
                ('stroke', models.CharField(max_length=100)),
                ('stroke_width', models.IntegerField(default=1)),
                ('stroke_opacity', models.FloatField(default=1.0)),
            ],
            bases=('gvsigol_symbology.symbolizer',),
        ),
        migrations.CreateModel(
            name='PolygonSymbolizer',
            fields=[
                ('symbolizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='gvsigol_symbology.Symbolizer')),
                ('fill', models.CharField(max_length=100)),
                ('fill_opacity', models.FloatField(default=1.0)),
                ('stroke', models.CharField(max_length=100)),
                ('stroke_width', models.IntegerField(default=1)),
                ('stroke_opacity', models.FloatField(default=1.0)),
            ],
            bases=('gvsigol_symbology.symbolizer',),
        ),
        migrations.CreateModel(
            name='RasterSymbolizer',
            fields=[
                ('symbolizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='gvsigol_symbology.Symbolizer')),
                ('opacity', models.FloatField(default=1.0)),
                ('color_map', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.ColorMap')),
            ],
            bases=('gvsigol_symbology.symbolizer',),
        ),
        migrations.CreateModel(
            name='TextSymbolizer',
            fields=[
                ('symbolizer_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='gvsigol_symbology.Symbolizer')),
                ('label', models.CharField(max_length=100)),
                ('font_family', models.CharField(max_length=100)),
                ('font_size', models.IntegerField(default=12)),
                ('font_style', models.CharField(max_length=100)),
                ('font_weight', models.CharField(max_length=100)),
                ('fill', models.CharField(max_length=100)),
                ('fill_opacity', models.FloatField(default=1.0)),
                ('halo_radius', models.IntegerField(default=12)),
                ('halo_fill', models.CharField(max_length=100)),
                ('halo_fill_opacity', models.FloatField(default=1.0)),
            ],
            bases=('gvsigol_symbology.symbolizer',),
        ),
        migrations.AddField(
            model_name='symbolizer',
            name='rule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.Rule'),
        ),
        migrations.AddField(
            model_name='rule',
            name='style',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.Style'),
        ),
        migrations.AddField(
            model_name='libraryrule',
            name='rule',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gvsigol_symbology.Rule'),
        ),
    ]
