# Generated by Django 5.0.6 on 2024-09-03 08:57

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eudr_backend', '0026_eudruploadedfilesmodel_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='eudrfarmmodel',
            name='site_id',
        ),
        migrations.AlterField(
            model_name='eudrusermodel',
            name='user_type',
            field=models.CharField(choices=[('AGENT', 'Agent'), ('ADMIN', 'Admin')], default='ADMIN', max_length=255),
        ),
        migrations.CreateModel(
            name='EUDRFarmBackupModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remote_id', models.CharField(blank=True, max_length=255, null=True)),
                ('farmer_name', models.CharField(max_length=255)),
                ('member_id', models.CharField(blank=True, max_length=255, null=True)),
                ('size', models.FloatField()),
                ('agent_name', models.CharField(blank=True, max_length=255, null=True)),
                ('village', models.CharField(max_length=255)),
                ('district', models.CharField(max_length=255)),
                ('latitude', models.FloatField(default=0.0)),
                ('longitude', models.FloatField(default=0.0)),
                ('coordinates', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('site_id', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='eudr_backend.eudrcollectionsitemodel')),
            ],
        ),
    ]
