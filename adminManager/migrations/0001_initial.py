# Generated by Django 3.2.11 on 2022-09-07 15:24

from django.db import migrations, models
import django.db.models.deletion
import djangowkb.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Admin',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.IntegerField(blank=True, null=True)),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_to', models.DateField(blank=True, null=True)),
                ('geom', djangowkb.fields.GeometryField(editable=True, geom_type='GEOMETRY', srid=None)),
            ],
        ),
        migrations.CreateModel(
            name='AdminName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='AdminSource',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('DataSource', 'Data Source'), ('MapSource', 'Map Source')], max_length=50)),
                ('name', models.CharField(max_length=200)),
                ('valid_from', models.DateField(blank=True, null=True)),
                ('valid_to', models.DateField(blank=True, null=True)),
                ('citation', models.TextField(blank=True, null=True)),
                ('note', models.TextField(blank=True, null=True)),
                ('url', models.URLField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(
            model_name='adminname',
            index=models.Index(fields=['name'], name='adminManage_name_4a5d6b_idx'),
        ),
        migrations.AddField(
            model_name='admin',
            name='names',
            field=models.ManyToManyField(related_name='admins', to='adminManager.AdminName'),
        ),
        migrations.AddField(
            model_name='admin',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='adminManager.admin'),
        ),
        migrations.AddField(
            model_name='admin',
            name='source',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='admins', to='adminManager.adminsource'),
        ),
    ]
