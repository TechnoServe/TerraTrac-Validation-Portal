# Generated by Django 5.0.6 on 2024-09-04 17:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eudr_backend', '0032_alter_eudrusermodel_user_type_customuser'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eudrusermodel',
            name='user_type',
            field=models.CharField(choices=[('AGENT', 'Agent'), ('ADMIN', 'Admin')], default='AGENT', max_length=255),
        ),
    ]
