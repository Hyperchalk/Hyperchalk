# Generated by Django 4.0.4 on 2023-03-23 14:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('collab', '0007_alter_excalidrawroom_room_consumer_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='excalidrawroom',
            name='tracking_enabled',
            field=models.BooleanField(default=True, verbose_name="track users' actions"),
        ),
        migrations.AlterField(
            model_name='coursetoroommapper',
            name='room',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True,
                related_name='course', serialize=False, to='collab.excalidrawroom', verbose_name='room name'),
        ),
        migrations.AlterField(
            model_name='coursetoroommapper',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL, verbose_name='user'),
        ),
    ]
