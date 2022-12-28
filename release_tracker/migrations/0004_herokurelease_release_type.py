# Generated by Django 3.2.16 on 2022-12-23 18:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("release_tracker", "0003_auto_20221223_0827"),
    ]

    operations = [
        migrations.AddField(
            model_name="herokurelease",
            name="release_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("DEPLOYMENT", "Code deployment"),
                    ("ADD_ON", "Add-ons"),
                    ("ENV_VARS", "Config vars"),
                    ("UNKNOWN", "Unknown"),
                ],
                default="UNKNOWN",
                max_length=10,
            ),
        ),
    ]