# Generated by Django 5.0.6 on 2024-07-23 10:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eudr_backend', '0014_eudrfarmmodel_geoid_alter_eudrusermodel_user_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eudrusermodel',
            name='user_type',
            field=models.CharField(choices=[('AGENT', 'Agent'), ('ADMIN', 'Admin')], default='ADMIN', max_length=255),
        ),
    ]
