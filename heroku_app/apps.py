from django.apps import AppConfig


class HerokuAppConfig(AppConfig):
    name = "heroku_app"
    verbose_name = "Heroku app deployment tracker"
    default_auto_field = "django.db.models.AutoField"
