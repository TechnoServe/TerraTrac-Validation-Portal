# Generated by Django 5.0.6 on 2024-07-18 09:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eudr_backend', '0012_eudrfarmmodel_remote_id_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='eudrfarmmodel',
            name='is_eudr_compliant',
        ),
        migrations.AlterField(
            model_name='eudrusermodel',
            name='user_type',
            field=models.CharField(choices=[('AGENT', 'Agent'), ('ADMIN', 'Admin')], default='ADMIN', max_length=255),
        ),
    ]
