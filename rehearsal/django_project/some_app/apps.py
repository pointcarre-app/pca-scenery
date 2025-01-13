from django.apps import AppConfig


class SomeAppConfig(AppConfig):
    """
    Dynamically configured based on called by
    python -m rehearsal
    OR
    python rehearsal/django_project/manage.py
    """

    default_auto_field = "django.db.models.BigAutoField"

    if __name__ == "rehearsal.django_project.some_app.apps":
        name = "rehearsal.django_project.some_app"
    elif __name__ == "some_app.apps":
        name = "some_app"
    else:
        raise Exception("Unexpected call.")
