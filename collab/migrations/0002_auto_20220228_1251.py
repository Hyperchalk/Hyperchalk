# Generated by Django 3.2.12 on 2022-02-28 11:51

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('lti1p3_tool_config', '0001_initial'),
        ('collab', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='excalidrawroom',
            name='room_consumer',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='lti1p3_tool_config.ltitool'),
        ),
        migrations.AddField(
            model_name='excalidrawroom',
            name='room_created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
    ]
