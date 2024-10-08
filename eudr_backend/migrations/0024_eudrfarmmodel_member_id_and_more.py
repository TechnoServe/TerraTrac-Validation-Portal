# Generated by Django 5.0.6 on 2024-08-29 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eudr_backend', '0023_eudrcollectionsitemodel_site_manager_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='eudrfarmmodel',
            name='member_id',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AlterField(
            model_name='eudrusermodel',
            name='user_type',
            field=models.CharField(choices=[('AGENT', 'Agent'), ('ADMIN', 'Admin')], default='ADMIN', max_length=255),
        ),
    ]
