# Generated by Django 5.0.6 on 2024-10-01 15:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eudr_backend', '0041_remove_eudruploadedfilesmodel_s3_file_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='eudrfarmbackupmodel',
            name='accuracies',
            field=models.JSONField(default=[]),
        ),
        migrations.AddField(
            model_name='eudrfarmmodel',
            name='accuracies',
            field=models.JSONField(default=[]),
        ),
        migrations.AlterField(
            model_name='eudrusermodel',
            name='user_type',
            field=models.CharField(choices=[('AGENT', 'Agent'), ('ADMIN', 'Admin')], default='AGENT', max_length=255),
        ),
    ]
