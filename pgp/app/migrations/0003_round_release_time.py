# Generated by Django 4.2.16 on 2024-09-22 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0002_round_playlist_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="round",
            name="release_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
