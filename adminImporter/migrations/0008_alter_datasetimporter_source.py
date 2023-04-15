# Generated by Django 3.2.16 on 2023-04-15 13:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('adminManager', '0005_adminname_admin_name_upper_idx'),
        ('adminImporter', '0007_alter_datasetimporter_import_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='datasetimporter',
            name='source',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='importers', to='adminManager.adminsource'),
        ),
    ]
