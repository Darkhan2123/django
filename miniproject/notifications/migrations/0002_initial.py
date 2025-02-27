# Generated by Django 5.1.6 on 2025-02-27 20:27

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('notifications', '0001_initial'),
        ('sales', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='related_invoice',
            field=models.ForeignKey(blank=True, help_text='Related invoice if applicable', null=True, on_delete=django.db.models.deletion.SET_NULL, to='sales.invoice'),
        ),
    ]
