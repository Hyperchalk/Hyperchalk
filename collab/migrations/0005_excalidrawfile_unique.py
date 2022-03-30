# Generated by Django 3.2.12 on 2022-03-29 17:20

from django.db import migrations, models
import django.db.models.deletion
import draw.utils


class Migration(migrations.Migration):

    replaces = [('collab', '0005_excalidrawfile'), ('collab', '0006_auto_20220329_1549')]

    dependencies = [
        ('collab', '0004_alter_excalidrawlogrecord_user_pseudonym'),
    ]

    operations = [
        migrations.AlterField(
            model_name='excalidrawlogrecord',
            name='room_name',
            field=models.CharField(max_length=24, validators=[draw.utils.validate_room_name]),
        ),
        migrations.AlterField(
            model_name='excalidrawroom',
            name='room_name',
            field=models.CharField(max_length=24, primary_key=True, serialize=False, validators=[draw.utils.validate_room_name]),
        ),
        migrations.CreateModel(
            name='ExcalidrawFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('element_file_id', models.CharField(max_length=40)),
                ('content', models.FileField(upload_to='excalidraw-uploads')),
                ('meta', models.JSONField(verbose_name='excalidraw meta data')),
                ('belongs_to', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='files', to='collab.excalidrawroom', verbose_name='belongs to room')),
            ],
            options={
                'unique_together': {('belongs_to', 'element_file_id')},
            },
        ),
    ]