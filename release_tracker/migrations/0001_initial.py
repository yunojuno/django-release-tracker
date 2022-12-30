# Generated by Django 4.1.4 on 2022-12-29 17:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="HerokuRelease",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("version", models.PositiveIntegerField(unique=True)),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Heroku release description (auto-generated).",
                    ),
                ),
                (
                    "slug_id",
                    models.UUIDField(
                        blank=True,
                        help_text="The slug id comes from the platform API or the config vars.",
                        null=True,
                    ),
                ),
                (
                    "commit",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Commit hash - pulled from Heroku API (/slugs), pushed to Github.",
                        max_length=40,
                    ),
                ),
                (
                    "commit_description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="The commit description pulled from the Heroku platform API.",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Release status pulled from Heroku platform API.",
                        max_length=100,
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the release was created by Heroku (from API).",
                        null=True,
                    ),
                ),
                (
                    "pulled_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the release data was pulled from Heroku",
                        null=True,
                    ),
                ),
                (
                    "pushed_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the release data was pushed to Github.",
                        null=True,
                    ),
                ),
                (
                    "heroku_release",
                    models.JSONField(
                        blank=True,
                        help_text="Release as represented by the Heroku platform API.",
                        null=True,
                    ),
                ),
                (
                    "github_release",
                    models.JSONField(
                        blank=True,
                        help_text="Release as represented by the Github REST API.",
                        null=True,
                    ),
                ),
                (
                    "release_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("DEPLOYMENT", "Slug deployment"),
                            ("PROMOTION", "Pipeline promotion"),
                            ("ROLLBACK", "Release rollback"),
                            ("ADD_ON", "Add-ons"),
                            ("ENV_VARS", "Config vars"),
                            ("OTHER", "Other (misc.)"),
                        ],
                        default="OTHER",
                        max_length=10,
                    ),
                ),
                (
                    "parent",
                    models.OneToOneField(
                        blank=True,
                        help_text="The previous release - used to generate changelog.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="release_tracker.herokurelease",
                        related_name="child",
                    ),
                ),
            ],
        ),
    ]
