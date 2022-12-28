from django.apps import AppConfig


class HerokuAppConfig(AppConfig):
    name = "release_tracker"
    verbose_name = "Heroku app deployment tracker"
    default_auto_field = "django.db.models.AutoField"
