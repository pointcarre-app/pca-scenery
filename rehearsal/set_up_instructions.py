import os

from django.apps import apps as django_apps
from django.db.models.deletion import ProtectedError
from django.test import Client

from rehearsal.project_django.some_app.models import SomeModel


def reset_db(django_testcase):
    """Delete all instances of all app models"""

    app_config = django_apps.get_app_config(os.getenv("SCENERY_TESTED_APP_NAME"))

    # NOTE: bug if kept as an iterator
    models = list(app_config.get_models())
    while any(model.objects.exists() for model in models):
        for model in models:
            try:
                model.objects.all().delete()
            except ProtectedError:
                continue


def login(django_testcase, *, user_email, password):
    """Login a test user"""
    django_testcase.client.login(username=user_email, password=password)


def create_some_instance(django_testcase, *, some_field):

    some_instance = SomeModel(some_field=some_field)
    some_instance.save()
