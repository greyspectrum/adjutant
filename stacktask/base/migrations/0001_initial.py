# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('api_v1', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Action',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_name', models.CharField(max_length=200)),
                ('action_data', jsonfield.fields.JSONField(default={})),
                ('cache', jsonfield.fields.JSONField(default={})),
                ('state', models.CharField(default=b'default', max_length=200)),
                ('valid', models.BooleanField(default=False)),
                ('need_token', models.BooleanField()),
                ('order', models.IntegerField()),
                ('created', models.DateTimeField(default=django.utils.timezone.now)),
                ('registration', models.ForeignKey(to='api_v1.Registration')),
            ],
        ),
    ]
